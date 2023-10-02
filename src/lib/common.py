from lib.utils import apply_query_params, json_loads_with_variables
import requests
from fastapi import HTTPException
from lib.models import *

def call(request: Request, keyspace: Dict, secrets: Dict):
    method = request.method
    url = request.url
    headers = request.headers
    data = request.data

    data_key = "params" if method.upper() == "GET" else "data"
    data_dict = {data_key:json.dumps(data)}

    if data_key == "data":
        headers["Content-Type"] = "application/json"

    try:
        inject_secret_options = keyspace["spec"]["inject-secret"]

        if "http-headers" in inject_secret_options.keys():
            for k,v in inject_secret_options["http-headers"].items():
                headers[k] = json_loads_with_variables(json.dumps(v), secrets)

        if "query-params" in inject_secret_options.keys():
            add_qparams = {}
            for k,v in inject_secret_options["query-params"].items():
                add_qparams[k] = json_loads_with_variables(json.dumps(v), secrets)
            
            url = apply_query_params(url, add_qparams)
            
    except:
        pass
    
    response = requests.request(url=url, method=method, headers=headers, **data_dict)  
    
    print(url, method, headers)

    if response.status_code > 300:
        raise HTTPException(status_code=response.status_code, detail=f"{response.json()}")

    return {"status_code": response.status_code, "headers": response.headers, "body": response.json()}