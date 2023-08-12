from pydantic import BaseModel
from typing import Union, Dict, List, Optional
from app.utils import path_params_from_url, apply_query_params, apply_path_params, json_loads_with_variables, eval_jsonpath_func
from collections import deque

import kubernetes as k8s
import requests

import json
from jsonpath_rw import jsonpath
from jsonpath_rw_ext import parse

query_kube = {
                'name': '$.metadata.name',
                'url': '$.spec.url',
                'method': '$.spec.method',
                'variables': '$.spec.variables',
                'variables_required': '$.spec.variables-required',
                'data': '$.spec.data',
                'result': '$.spec.result',
            }
    
def read_kube(jsonpath, kube_resource):
    try:
        return parse(jsonpath).find(kube_resource)[0].value
    except IndexError:
        raise AttributeError

class Query(BaseModel):
    name: str = ''
    url: str = ''
    method: str = 'GET'
    variables: Dict = {}
    variables_required: List = []
    data: str = '{}'
    result: Dict = {}

    def init_from_kube(self, kube_resource):
        for k,v in query_kube.items():
            try:
                value = read_kube(v, kube_resource)
                setattr(self, k, value)

            except AttributeError:
                continue
        return self

    def apply(self, params):
        path_params_keys = path_params_from_url(self.url)
        required_variables = {k for k,v in self.variables.items() if v in self.variables_required and 'default' not in v.keys()}

        required_params_keys = path_params_keys.union(required_variables)
        params_not_provided =  required_params_keys - set(params.keys())

        if len(params_not_provided) > 0:
            raise KeyError(params_not_provided)

        path_params = {k:params[k] for k in path_params_keys}
        url = apply_path_params(self.url, path_params)

        func = {'int': int, 'string': str}
        var_values = {}
        for k,v in self.variables.items():
            f = func[v['type']]

            if k in params.keys():
                var_values[k] = f(params[k])
            elif "default" in v.keys():
                var_values[k] = f(v["default"])

        if self.method == "GET":
            url = apply_query_params(url, var_values)
            data = None
        else:
            try:
                data = json_loads_with_variables(self.data, var_values)
            except json.decoder.JSONDecoderError:
                data = var_values

        data_string = json.dumps(data)

        return url, data_string

    def get_result(self, body, data:Optional[Dict] = None, result_targets:Optional[List] = None):
        res = {}

        q = result_targets or [k for k in self.result.keys()]
        q = set(q).intersection(self.result.keys())
        q = deque(q)

        data = data or {}

        required = {k:path_params_from_url(v) for k,v in self.result.items()}

        while q:
            k = q.pop()
            if len(required[k] - res.keys()) > 0:
                q.extendleft(required[k] - set(q))      # insert required parameters to the queue, if they don't exist
                q.appendleft(k)                         # insert self again
                continue

            res[k] = data[k] = eval_jsonpath_func(self.result[k], body, data)

        return res

def get_all_queries_from_kube():
    k8s.config.load_incluster_config()
    queries = k8s.client.CustomObjectsApi().list_namespaced_custom_object(group="queries.api-callers.io", 
                                                                        version="v1", 
                                                                        plural="apiqueries", 
                                                                        namespace="api-callers",
                                                                        label_selector="queries.api-callers.io/keyspace=riot")['items']
    return {q['metadata']['name']:Query().init_from_kube(q) for q in queries}

def get_query_from_kube(query):
    k8s.config.load_incluster_config()
    q = k8s.client.CustomObjectsApi().get_namespaced_custom_object(group="queries.api-callers.io", 
                                                                        version="v1", 
                                                                        plural="apiqueries", 
                                                                        namespace="api-callers",
                                                                        name=query)
    return Query().init_from_kube(q)

def get_all_queries():
    # TODO : support query database other than kube crd
    return get_all_queries_from_kube()

def get_query(query):
    # TODO : support query database other than kube crd
    return get_query_from_kube(query)

class Request(BaseModel):
    url: str
    method: str = "GET"
    data: Dict = {}
    headers: Dict = {}

def send_to_caller(reqs: List[Request]):
    headers = {"Content-Type": "application/json"}
    responses = [requests.post('http://api-caller:80/call', headers=headers, data=json.dumps(dict(req))) for req in reqs]

    return responses