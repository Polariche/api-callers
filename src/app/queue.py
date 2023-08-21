from fastapi import FastAPI, HTTPException
from typing import Union, Dict, List
from collections import deque
import requests
import redis
import json
import os


from lib.models import *
from lib.redis_queue import RedisQueue
from lib.utils import path_params_from_url, kube_get_keyspace

app = FastAPI()
r = redis.Redis(host='redis', port=6379, decode_responses=True)

app.queueid = os.environ['QUEUE_ID']
app.keyspace = kube_get_keyspace()

app.redis_queue = RedisQueue(r, app, app.queueid)

@app.get("/query")
def top():
    return app.redis_queue.peek()

@app.get("/query/{query}")
def top_query(query: str):
    return app.redis_queue.peek_query(query)

@app.post("/query/{query}")
def post_query(query: str, params: Dict):
    try:
        query_model = app.queries[query]
    except:
        raise HTTPException(status_code=404, detail=f"Query not found")

    try:
        query_model.validate(params)
        app.redis_queue.post_query(query, params)
        
    except KeyError as e: 
        raise HTTPException(status_code=422, detail=f"Following variables must be defined: {e.args[0]}")

    return {"query": query, "params": params}

def _delete(count: int=1, query=None):
    if count <= 0:
        raise HTTPException(status_code=422, detail="count must be at least 1")
    
    reqs, queries = app.redis_queue.pop_requests(count=count, query=query)
    
    if len(reqs) < 1:
        raise HTTPException(status_code=404, detail="no queries left in the query")
    
    return reqs, queries

@app.delete("/query")
def delete_top(count: int = 1):
    reqs, queries = _delete(count, None)
    return {"queries": queries, "requests": reqs} 

@app.delete("/query/{query}")
def delete_query(query: str, count: int = 1):
    reqs, queries = _delete(count, query)
    return {"queries": queries, "requests": reqs} 

def _send(count: int=1, query=None):
    reqs, queries = _delete(count=count, query=query)
    responses = send_to_caller(reqs)

    outputs = []
    for req, response, query in zip(reqs, responses, queries):
        q = app.queries[query]
        req.data.update(path_params_from_url(req.url, q.url))
        
        try:
            output = q.get_output(response.json()['body'], data=req.data)
            
        except KeyError:
            output = {'detail': response.json()['detail']}
            
        outputs.append(output)   
        
    return outputs 

@app.get("/send")
def send(count: int = 1):
    return _send(query=None, count=count)

@app.get("/send/query/{query}")
def send_query(query: str, count: int = 1):
    return _send(query=query, count=count)

@app.get("/apiqueries")
def available_API_queries():
    # fetch and update queries
    app.queries = get_all_queries()
    return app.queries

@app.get("/ready")
def ready():
    try:
        requests.get(f'http://qourier-caller-{app.keyspace}:80')
    except:
        raise HTTPException(status_code=500, detail=f"No API Callers are available. Please try again.")

    return "ready"

@app.get("/metrics")
def metrics():
    return {}
