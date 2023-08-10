from fastapi import FastAPI, HTTPException
from fastapi.param_functions import Depends
from typing import Union, Dict
import requests
import redis
import json

import kubernetes as k8s

from app.models import *

app = FastAPI()
r = redis.Redis(host='redis', port=6379, decode_responses=True)

app.queueid = 'queueid'

k8s.config.load_incluster_config()
queries = k8s.client.CustomObjectsApi().list_namespaced_custom_object(group="queries.api-callers.io", version="v1", plural="apiqueries", namespace="api-callers")['items']
app.queries = {q['metadata']['name']:Query(kube_resource=q).init_from_kube() for q in queries}

def send_to_caller(request: Request):
    res = requests.post('http://api-caller:80/call', data=dict(request))
    
@app.get("/")
def top():
    return {}

@app.delete("/")
def delete_top():
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
    if data is not None:
        r.lpush(f"queue:{app.queueid}:{query}:var", data)

    return {"query": query, "params": params}

@app.delete("/query/{query}")
def delete_query(query: str):
    return {"query": query}

def fetch_requests(query, count):
    method = app.queries[query].method
    urls = r.rpop(f"queue:{app.queueid}:{query}:url", count)

    if method != "GET":
        vars = r.rpop(f"queue:{app.queueid}:{query}:var", count)
        return [Request(url=url, method=method, data=json.loads(var)) for url, var in zip(urls, vars)]
    else:
        return [Request(url=url, method=method) for url in urls]

@app.get("/send")
def send(count: int = 1):
    assert count > 0, "count must be at least 1"

    queries = r.rpop(f"queue:{app.queueid}")
    q_count = {q:queries.count(q) for q in set(queries)}
    requests = []

    for query,count in q_count.items():
        requests += fetch_requests(query, count)

    return requests

@app.get("/send/query/{query}")
def send_query(query: str, count: int = 1):
    assert count > 0, "count must be at least 1"

    r.lrem(f"queue:{app.queueid}", query, count)
    requests = fetch_requests(query, count)

    return requests

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
