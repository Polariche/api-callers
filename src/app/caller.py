from fastapi import FastAPI, HTTPException
from typing import Union
import requests
import redis
import os

import kubernetes as k8s

from lib.api_key import Key
from lib.models import *
from lib.utils import apply_query_params

r = redis.Redis(host='redis', port=6379, decode_responses=True)

app = FastAPI()
app.available = False

app.key_id = os.environ['KEY_ID']
app.keyspace = os.environ['KEYSPACE']
app.key = Key(r, app.key_id)

k8s.config.load_incluster_config()
keyspace = k8s.client.CustomObjectsApi().get_namespaced_custom_object(group="keys.qouriers.io", 
                                                                        version="v1", 
                                                                        plural="keyspaces", 
                                                                        namespace="qouriers",
                                                                        name=app.keyspace)

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
    data = request.data

    data_key = "params" if method.upper() == "GET" else "data"
    data_dict = {data_key:json.dumps(data)}

    if data_key == "data":
        headers["Content-Type"] = "application/json"

    try:
        inject_key_options = keyspace["spec"]["inject-key"]

        if "http-headers" in inject_key_options.keys():
            for k,v in inject_key_options["http-headers"].items():
                headers[k] = v.format(key=app.key.secret)

        if "query-params" in inject_key_options.keys():
            add_qparams = {}
            for k,v in inject_key_options["query-params"].items():
                add_qparams[k] = v.format(key=app.key.secret)
            
            url = apply_query_params(url, add_qparams)
            
    except:
        pass
    
    app.key.use()
    response = requests.request(url=url, method=method, headers=headers, **data_dict)  

    if response.status_code > 300:
        raise HTTPException(status_code=response.status_code, detail=f"{response.json()}")

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

