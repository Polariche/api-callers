from pydantic import BaseModel
from typing import Union, Dict, List, Optional
from lib.utils import path_param_keys_from_path, apply_query_params, apply_path_params, json_loads_with_variables, eval_jsonpath_func, kube_get_keyspace
from collections import deque

import os

import kubernetes as k8s
import requests

import json
from jsonpath_rw_ext import parse

query_kube = {
                'name': '$.metadata.name',
                'keyspace': '$.metadata.labels["keys.qouriers.io/keyspace"]',
                'url': '$.spec.url',
                'method': '$.spec.method',
                'input': '$.spec.input',
                'input_required': '$.spec.input-required',
                'data': '$.spec.data',
                'output': '$.spec.output',
            }
    
def read_kube(jsonpath, kube_resource):
    try:
        return parse(jsonpath).find(kube_resource)[0].value
    except IndexError:
        raise AttributeError

class Query(BaseModel):
    name: str = ''
    keyspace: str = ''
    url: str = ''
    method: str = 'GET'
    input: Dict = {}
    input_required: List = []
    data: str = '{}'
    output: Dict = {}

    def init_from_kube(self, kube_resource):
        for k,v in query_kube.items():
            try:
                value = read_kube(v, kube_resource)
                setattr(self, k, value)

            except AttributeError:
                continue
        return self
    
    def validate(self, params):
        path_params_keys = path_param_keys_from_path(self.url)
        required_input = {k for k,v in self.input.items() if v in self.input_required and 'default' not in v.keys()}

        required_params_keys = path_params_keys.union(required_input)
        params_not_provided =  required_params_keys - set(params.keys())

        if len(params_not_provided) > 0:
            raise KeyError(params_not_provided)

    def apply(self, params):
        self.validate(params)
        
        path_params_keys = path_param_keys_from_path(self.url)
        path_params = {k:params[k] for k in path_params_keys}
        url = apply_path_params(self.url, path_params)

        typefunc = {'str': str, 'string': str, 'int': int, 'integer': int, 'float': float}
        var_values = {}
        for k,v in self.input.items():
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
        
        for readtype, outputset in self.output.items():
            # TODO : implement HTML parsing
            # we only have JSON for now 
            
            q = output_targets or [k for k in outputset.keys()]
            q = set(q).intersection(outputset.keys())
            q = deque(q)

            data = data or {}

            required = {k:path_param_keys_from_path(v) for k,v in outputset.items()}

            while q:
                k = q.pop()
                if len(required[k] - data.keys()) > 0:
                    q.extendleft(required[k] - set(q))      # insert required parameters to the queue, if they don't exist
                    q.appendleft(k)                         # insert self again
                    continue

                res[k] = data[k] = eval_jsonpath_func(outputset[k], body, data)

        return res

def get_all_queries_from_kube(keyspace=None):
    kwargs = {}
    #if keyspace != None:
    #    kwargs = {"label_selector": f"keys.qouriers.io/keyspace={keyspace}"}
    
    k8s.config.load_incluster_config()
    queries = k8s.client.CustomObjectsApi().list_namespaced_custom_object(group="queries.qouriers.io", 
                                                                        version="v1", 
                                                                        plural="apiqueries", 
                                                                        namespace="qouriers")['items']
    
    return {q['metadata']['name']:Query().init_from_kube(q) for q in queries}

def get_query_from_kube(query):
    k8s.config.load_incluster_config()
    q = k8s.client.CustomObjectsApi().get_namespaced_custom_object(group="queries.qouriers.io", 
                                                                        version="v1", 
                                                                        plural="apiqueries", 
                                                                        namespace="qouriers",
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

def send_to_caller(reqs: List[Request], keyspaces: List[str]):
    headers = {"Content-Type": "application/json"}
    responses = [requests.post(f'http://qourier-caller-{keyspace}:80/call', headers=headers, data=json.dumps(dict(req))) for req,keyspace in zip(reqs, keyspaces)]

    return responses