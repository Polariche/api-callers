from fastapi import FastAPI, HTTPException
import redis
import os

from lib.api_key import Key
from lib.models import *
from lib.kube_utils import kube_find_my_keyspace, kube_get_keyspace
from lib.common import call

app = FastAPI()
app.available = False

r = redis.Redis(host='redis', port=6379, decode_responses=True)
app.key_id = os.environ['KEY_ID']
app.key = Key(r, app.key_id)

app.keyspace_name = kube_find_my_keyspace()

def check_available():
    app.available, seconds, waitseconds = app.key.is_available()
    if not app.available:
        raise HTTPException(status_code=429, detail=f"API Key has exceeded rate limits. Please try again after {waitseconds} seconds.")

@app.post("/call")
def make_call(request: Request):
    check_available()
    
    keyspace = kube_get_keyspace(app.keyspace_name)
    secrets = app.key.get_secrets()
    
    response = call(request, keyspace, secrets)
    app.key.use()
    
    return response
    
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

