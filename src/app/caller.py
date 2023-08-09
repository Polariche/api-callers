from fastapi import FastAPI, HTTPException
from typing import Union
import requests as re
import redis
import os

from app.api_key import Key
from app.models import *

key_id = os.environ['KEY_ID']

r = redis.Redis(host='redis', port=6379, decode_responses=True)
k = Key(r, key_id)

app = FastAPI()

@app.get("/")
def root():
    return {"key_id": key_id}

@app.post("/call")
def call(request: Request):
    err_status_code = 500

    method = request.method
    url = request.url
    headers = request.headers

    data = dict(request.data or {})
    data_key = "params" if method.upper() == "GET" else "data"
    data_dict = {data_key:data}

    if data_key == "data":
        headers["Content-Type"] = "application/json"
    
    k.use()
    response = re.request(url=url, method=method, headers=headers, **data_dict)  
    err_status_code = response.status_code

    return response.json()
    

@app.get("/ready")
def ready():
    # caller is Ready
    # if API key exists & not rate-limited
    available, seconds, waitseconds = k.is_available()
    if not available:
        raise HTTPException(status_code=429, detail=f"API Key has exceeded rate limits. Please try again after {waitseconds} seconds.")

    return True

@app.get("/healthy")
def healthy():
    # caller is Healthy
    # if API key exists & API key is valid (not expired)

    return True

@app.get("/metrics")
def metrics():
    return {}

