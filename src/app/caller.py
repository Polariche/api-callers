from fastapi import FastAPI, HTTPException
from typing import Union
import requests
import redis
import os

from app.api_key import Key
from app.models import *

r = redis.Redis(host='redis', port=6379, decode_responses=True)

app = FastAPI()
app.available = False

app.key_id = os.environ['KEY_ID']
app.key = Key(r, app.key_id)

def check_available():
    app.available, seconds, waitseconds = app.key.is_available()
    if not app.available:
        raise HTTPException(status_code=429, detail=f"API Key has exceeded rate limits. Please try again after {waitseconds} seconds.")

@app.get("/")
def root():
    return {"key_id": app.key_id}

@app.post("/call")
def call(request: Request):
    check_available()

    method = request.method
    url = request.url
    headers = request.headers

    data = dict(request.data or {})
    data_key = "params" if method.upper() == "GET" else "data"
    data_dict = {data_key:data}

    if data_key == "data":
        headers["Content-Type"] = "application/json"
    
    app.key.use()
    response = requests.request(url=url, method=method, headers=headers, **data_dict)  

    return {"status_code": response.status_code, "headers": response.headers, "body": response.json()}
    
@app.get("/count")
def count():
    return app.key.get_count()

@app.get("/max")
def max():
    return app.key.get_max()

@app.get("/ready")
def ready():
    # caller is Ready
    # if API key exists & not rate-limited
    check_available()

    return True

@app.get("/healthy")
def healthy():
    # caller is Healthy
    # if API key exists & API key is valid (not expired)

    return True

@app.get("/metrics")
def metrics():
    return {}

