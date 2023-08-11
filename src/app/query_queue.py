from fastapi import FastAPI, HTTPException
from fastapi.param_functions import Depends
from typing import Union, Dict, List
from collections import deque
import requests
import redis
import json

import kubernetes as k8s

from app.models import *

app = FastAPI()
r = redis.Redis(host='redis', port=6379, decode_responses=True)

app.queueid = 'queueid'

k8s.config.load_incluster_config()
queries = k8s.client.CustomObjectsApi().list_namespaced_custom_object(group="queries.api-callers.io", 
                                                                        version="v1", 
                                                                        plural="apiqueries", 
                                                                        namespace="api-callers",
                                                                        label_selector="queries.api-callers.io/keyspace=riot")['items']

app.queries = {q['metadata']['name']:Query().init_from_kube(q) for q in queries}

def send_to_caller(reqs: List[Dict]):
    headers = {"Content-Type": "application/json"}
    responses = [requests.post('http://api-caller:80/call', headers=headers, data=json.dumps(dict(req))) for req in reqs]

    return responses

def pop_requests(query, count):
    method = app.queries[query].method
    urls = r.rpop(f"queue:{app.queueid}:{query}:url", count)

    if method != "GET":
        vars = r.rpop(f"queue:{app.queueid}:{query}:var", count)
        return [Request(url=url, method=method, data=json.loads(var)) for url, var in zip(urls, vars)]
    else:
        return [Request(url=url, method=method) for url in urls]

def _delete_top(count: int = 1):
    if count <= 0:
        raise HTTPException(status_code=422, detail="count must be at least 1")

    queries = r.rpop(f"queue:{app.queueid}", count)
    if queries is None:
        raise HTTPException(status_code=404, detail="There are no queries left in the queue")

    qcounts = {q:queries.count(q) for q in set(queries)}
    reqs = {}

    for query,qcount in qcounts.items():
        reqs[query] = deque(pop_requests(query, qcount))

    requests = deque()
    for q in queries:
        requests.append(reqs[q].popleft())

    return list(requests), queries

def _delete_query(query: str, count: int = 1):
    if count <= 0:
        raise HTTPException(status_code=422, detail="count must be at least 1")

    count = r.lrem(f"queue:{app.queueid}", -count, query)
    if count <= 0:
        raise HTTPException(status_code=404, detail=f"There are no queries({query}) left in the queue")
        
    requests = pop_requests(query, count)

    return requests

@app.get("/")
def top():
    return {}

@app.get("/query/{query}")
def top_query(query: str):
    return {"query": query}

@app.post("/query/{query}")
def post_query(query: str, params: Dict):
    try:
        query_model = app.queries[query]
    except:
        raise HTTPException(status_code=404, detail=f"Query not found")

    url, data = query_model.apply(params)

    r.lpush(f"queue:{app.queueid}", query)
    r.lpush(f"queue:{app.queueid}:{query}:url", url)

    if data is not "null":
        r.lpush(f"queue:{app.queueid}:{query}:var", data)
        return {"query": query, "url": url, "data": data}

    else:
        return {"query": query, "url": url}

@app.delete("/")
def delete_top(count: int = 1):
    reqs, queries = _delete_top(count)
    return {"queries": queries, "requests": reqs}

@app.delete("/query/{query}")
def delete_query(query: str, count: int = 1):
    reqs = _delete_query(query, count)
    return {"requests": reqs}

@app.get("/send")
def send(count: int = 1):
    reqs, queries = _delete_top(count)
    responses = send_to_caller(reqs)

    results = [app.queries[query].get_result(response.json()['body'], data=req.data) for req, response, query in zip(reqs, responses, queries)]
    
    return results

@app.get("/send/query/{query}")
def send_query(query: str, count: int = 1):
    reqs = _delete_query(query, count)
    responses = send_to_caller(reqs)

    results = [app.queries[query].get_result(response.json()['body'], data=req.data) for req, response in zip(reqs, responses)]

    return results

@app.get("/apiqueries")
def available_API_queries():
    return app.queries

@app.get("/ready")
def ready():
    try:
        requests.get('http://api-caller:80')
    except:
        raise HTTPException(status_code=500, detail=f"No API Callers are available. Please try again.")

    return "ready"

@app.get("/metrics")
def metrics():
    return {}
