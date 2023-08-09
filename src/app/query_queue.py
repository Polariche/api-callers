from fastapi import FastAPI, HTTPException
from fastapi.param_functions import Depends
from typing import Union, Dict
import requests as re
import redis
from app.models import *

app = FastAPI()
r = redis.Redis(host='redis', port=6379, decode_responses=True)


def push_to_caller(request: Request):
    res = re.post('http://api-caller:80/call', data=dict(request))


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
    return {"query": query, "params": params}

@app.delete("/query/{query}")
def delete_query(query: str):
    return {"query": query}

@app.get("/push")
def push():
    return {}

@app.get("push/query/{query}")
def push_query(query: str):
    return {}


@app.get("/ready")
def ready():
    try:
        re.get('http://api-caller:80')
    except:
        raise HTTPException(status_code=500, detail=f"No API Callers are available. Please try again.")

    return "ready"

#@app.get("/healthy")
#def healthy():
#    return "healthy"

@app.get("/metrics")
def metrics():
    return {}
