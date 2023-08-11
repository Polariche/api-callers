from pydantic import BaseModel
from typing import Union, Dict, List, Optional
from app.utils import path_params_from_url, apply_query_params, apply_path_params, json_loads_with_variables
from collections import deque

import json
from jsonpath_rw import jsonpath
from jsonpath_rw_ext import parse

query_kube = {
                'name': '$.metadata.name',
                'url': '$.spec.url',
                'method': '$.spec.method',
                'variables': '$.spec.variables',
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
        required_variables = {k for k,v in self.variables.items() if v['required']}

        required_params_keys = path_params_keys.union(required_variables)
        params_not_provided = set(params.keys()) - required_params_keys
        assert len(params_not_provided) == 0, f"Required parameters are not provided: {params_not_provided}"

        path_params = {k:params[k] for k in path_params_keys}
        url = apply_path_params(self.url, path_params)

        func = {'int': int, 'string': str}
        var_values = {k:func[v['type']](params[k] or v['default']) for k,v in self.variables.items() if k in params.keys() or 'default' in v.values()}
        
        if self.method == "GET":
            url = apply_query_params(url, var_values)
            data = {}
        else:
            try:
                data = json_loads_with_variables(self.data, var_values)
            except json.decoder.JSONDecoderError:
                data = var_values

        data_string = json.dumps(data)

        return url, data_string

    def get_result(self, body, params:Optional[Dict], headers:Optional[Dict], result_targets:Optional[List]):
        res = {}

        q = result_targets or [k for k,v in self.result.keys()]
        q = set(q).intersection(self.result.keys())
        q = deque(q)

        params = params or {}

        required = {k:path_params_from_url(v) for k,v in self.result.items()}

        while q:
            k = q.pop()
            if len(reqs[k] - res.keys()) > 0:
                q.extendleft(required[k] - set(q))      # insert required parameters to the queue, if they don't exist
                q.appendleft(k)                         # insert self again
                continue

            # TODO: add support for max(jsonpath), min(jsonpath), and regex(jsonpath, pattern)
            res[k] = params[k] = parse_jsonpath_with_variables(self.result[k], body, params)

        return res

class Request(BaseModel):
    url: str
    method: str = "GET"
    data: Dict = {}
    headers: Dict = {}