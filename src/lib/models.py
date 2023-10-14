from pydantic import BaseModel
from typing import Union, Dict, List, Optional
from lib.utils import path_param_keys_from_path, apply_query_params, apply_path_params, json_loads_with_variables, eval_jsonpath_func, eval_css_selector_func
from lib.kube_utils import kube_query_jsonpath, kube_load_query, kube_get_queries

from collections import deque
import requests

import json

class Query(BaseModel):
    name: str = ''
    keyspace: str = ''
    url: str = ''
    method: str = 'GET'
    input: Dict = {'args':{}}
    data: str = '{}'
    output: Dict = {}

    def init_from_kube(self, kube_resource):
        for k,v in kube_query_jsonpath.items():
            try:
                value = kube_load_query(v, kube_resource)
                setattr(self, k, value)

            except AttributeError:
                continue
        return self
    
    def validate(self, params):
        path_params = path_param_keys_from_path(self.url)
        query_params = {k for k,v in self.input['args'].items() if 'required' in v.keys() and 'default' not in v.keys()}
        required_params = path_params.union(query_params)
        params_not_provided =  required_params - set(params.keys())

        if len(params_not_provided) > 0:
            raise KeyError(params_not_provided)

    def apply(self, params):
        self.validate(params)
        
        path_params_keys = path_param_keys_from_path(self.url)
        path_params = {k:params[k] for k in path_params_keys}
        url = apply_path_params(self.url, path_params)

        typefunc = {'str': str, 'string': str, 'int': int, 'integer': int, 'float': float}
        var_values = {}
        for k,v in self.input['args'].items():
            f = typefunc[v['type']]

            if k in params.keys():
                var_values[k] = f(params[k])
            elif "default" in v.keys():
                var_values[k] = f(v["default"])

        if self.method == "GET":
            url = apply_query_params(url, var_values)
            data = {}
        else:
            try:
                data = json_loads_with_variables(self.data, var_values)
            except:
                data = var_values

        return Request(url=url, method=self.method, data=data)

    def get_output(self, body, data:Optional[Dict] = None, output_targets:Optional[List] = None):
        res = {}
        
        # TODO : implement HTML parsing
        # we only have JSON for now 
        q = output_targets or [k for k in self.output['args'].keys()]
        q = set(q).intersection(self.output['args'].keys())
        q = deque(q)

        data = data or {}

        required = {k:path_param_keys_from_path(v) for k,v in self.output['args'].items()}

        while q:
            k = q.pop()
            
            if len(required[k] - data.keys()) > 0:
                q.extendleft(required[k] - set(q))      # insert required parameters to the queue, if they don't exist
                q.appendleft(k)                         # insert self again
                continue
            
            v = self.output['args'][k]
            v = v.format(**data)
            
            if self.output['parseType'] == "json":
                res[k] = data[k] = eval_jsonpath_func(v, body)
            elif self.output['parseType'] == "html":
                res[k] = data[k] = eval_css_selector_func(v, body)
            else:
                continue
            
            #body = json_loads_with_variables(json.dumps(body), data)

        return res

def get_all_queries():
    # TODO : support query database other than kube crd
    queries = kube_get_queries()
    return {q['metadata']['name']:Query().init_from_kube(q) for q in queries}

class Request(BaseModel):
    url: str
    method: str = "GET"
    data: Dict = {}
    headers: Dict = {}

def send_to_caller(reqs: List[Request], keyspaces: List[str]):
    headers = {"Content-Type": "application/json"}
    responses = [requests.post(f'http://qourier-caller-{keyspace}:80/call', headers=headers, data=json.dumps(dict(req))) for req,keyspace in zip(reqs, keyspaces)]

    return responses