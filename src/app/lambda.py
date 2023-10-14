from fastapi import FastAPI, HTTPException
from typing import Union, Dict, List

from lib.models import get_all_queries
from lib.kube_utils import kube_get_keyspace
from lib.common import call

# lightweight, all-in-one version of qourier 

app = FastAPI()
app.queries = get_all_queries()
keyspace = kube_get_keyspace("lostark")
secrets = {}

with open("/data/secrets/token") as f:
    secrets["token"] = ''.join(f.readlines())

@app.post("/{query}")
def quick_query(query: str, params: Dict):
    try:
        q = app.queries[query]
    except:
        raise HTTPException(status_code=404, detail=f"Query not found")

    try:
        request = q.apply(params)
        
    except KeyError as e: 
        raise HTTPException(status_code=422, detail=f"Following variables must be defined: {e.args[0]}")

    response = call(request, keyspace, secrets)
    
    try:
        body = response['body']
    except KeyError:
        raise HTTPException(status_code=response.status_code, detail=f"Got an error message : {response['detail']}")
    
    output = q.get_output(body, data=params)

    return output
