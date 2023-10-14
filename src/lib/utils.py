import re
import json
import itertools
import base64

from jsonpath_rw import jsonpath
from jsonpath_rw_ext import parse

from lib.parse_functions import *
from bs4 import BeautifulSoup

varname_regex = '[\w_][\w\d_-]*'
path_regex = '^(\w*://)?((?:[\w\d_-]*\.)*[\w\d_-]*)?(?:\:(\d*))?((?:/[\w\d\._-\{\}]*)*)?'
jsonpath_regex = '(?:\$|\.[\w_][\w\d_-]*|\[[^\[\]\s]*\])*'

def deconstruct_url(url):
    res = {}
    res['protocol'], res['host'], res['port'], res['path'] = re.findall(path_regex, url)[0]
    try:
        res['port'] = int(res['port'])
    except (TypeError, ValueError):
        res['port'] = None

    return res

def path_param_keys_from_path(url):
    return set(re.findall('\{([\w_][\w\d_-]*)\}', url))

def path_params_from_url(url, path):
    # url is the applied url, path is the template url

    url_path = deconstruct_url(url)['path']
    path = deconstruct_url(path)['path']
    
    u_splits = url_path.split('/')[1:]
    p_splits = re.findall('\{([\w_][\w\d_-]*)\}|([\w_][\w\d_-]*)', path)

    return {p[0]:u for u,p in zip(u_splits, p_splits) if len(p[0]) > 0}

def query_params_from_url(url):
    detached_url = re.match(path_regex, url).string
    params = re.findall(f'[\&\?]({varname_regex})=([^\s\&]*)', url)
    return detached_url, dict(params)

def apply_path_params(url, params):
    return url.format(**params)

def apply_query_params(url, params):
    url, old_params = query_params_from_url(url)
    old_params.update(params)

    if len(old_params.keys()) > 0:
        url = url+'?'+'&'.join([f'{k}={v}' for k,v in old_params.items()])

    return url

def json_loads_with_variables(json_string, variables):
    finds = re.findall('(\{([\w_][\w\d_-]*)\})', json_string)

    if set(variables.keys()).intersection({f[1] for f in finds}):
        for ms, k in finds:
            json_string = json_string.replace(ms, str(variables[k]))
    
    json_obj = json.loads(json_string)
        
    return json_obj

def eval_jsonpath_func(jsonpath_s, content):
    # recursively parse with jsonpath from content
    try:
        func_name, jsonpath_s = re.findall(f'({varname_regex})\((.*)\)', jsonpath_s)[0]
        result = eval_jsonpath_func(jsonpath_s, content)

        return getattr(JsonPath, func_name)(result)

    except IndexError:
        return [m.value for m in parse(jsonpath_s).find(content)]
    

def eval_css_selector_func(selector_s, content):
    # recursively parse with jsonpath from content
    try:
        func_name, selector_s = re.findall(f'({varname_regex})\((.*)\)', selector_s)[0]
        result = eval_css_selector_func(selector_s, content)

        return getattr(CssSelector, func_name)(result)

    except IndexError:
        soup = BeautifulSoup(content, 'html.parser')
        return [m.text for m in soup.select(selector_s)]
    

def flatten_dict(d):
    return itertools.chain(*d.items())

def json_to_byte(j):
    return base64.b64encode(json.dumps(j).encode("utf-8")).decode("utf-8")

def byte_to_json(j):
    return json.loads(base64.b64decode(j.encode("utf-8")).decode("utf-8"))