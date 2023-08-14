from fastapi import FastAPI, HTTPException
from typing import Union, Dict, List
from collections import deque
import requests
import redis
import json

from app.models import *

app = FastAPI()

@app.post("/query/{query}")
def post_query(query: str, params: Dict):
    try:
        q = get_query(query)
        method = q.method
    except:
        raise HTTPException(status_code=404, detail=f"Query not found")

    try:
        url, var = q.apply(params)
        if var is not "null":
            req = Request(url=url, method=method, data=json.loads(var))
        else:
            req = Request(url=url, method=method)

    except KeyError as e: 
        raise HTTPException(status_code=422, detail=f"Following variables must be defined: {e.args[0]}")
    
    response = send_to_caller([req])[0]
    
    try:
        body = response.json()['body']
    except KeyError:
        raise HTTPException(status_code=response.status_code, detail=f"Got an error message : {response.json()['detail']}")
    
    result = q.get_result(body, data=params)

    return result

@app.get("/apiqueries")
def available_API_queries():
    return get_all_queries()

@app.get("/ready")
def ready():
    try:
        requests.get(f'http://qourier-caller-{os.environ["KEYSPACE"]}:80')
    except:
        raise HTTPException(status_code=500, detail=f"No API Callers are available. Please try again.")

    return "ready"

@app.get("/metrics")
def metrics():
    return {}
