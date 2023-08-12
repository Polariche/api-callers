import re
import json
from jsonpath_rw import jsonpath
from jsonpath_rw_ext import parse

from app.jsonpath_functions import jsonpath_functions

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
    finds = re.findall('(\{\s*([\w_][\w\d_-]*)\s*\})', json_string)

    if set(variables.keys()).intersection({f[1] for f in finds}):
        for ms, k in finds:
            json_string = json_string.replace(ms, str(variables[k]))
    
    json_obj = json.loads(json_string)
        
    return json_obj

def eval_jsonpath_func(jsonpath_s, content, variables):
    regex = f'({varname_regex})\(\s*({jsonpath_regex})\s*\)'
    try:
        func_name, jsonpath_s = re.findall(regex, jsonpath_s)[0]
        result = eval_jsonpath_func(jsonpath_s, content, variables)

        return jsonpath_functions[func_name](result)

    except IndexError:
        return parse_jsonpath_with_variables(jsonpath_s, content, variables)
    
def parse_jsonpath_with_variables(jsonpath_s, content, variables):
    if len(variables.keys()) > 0:
        jsonpath_s = jsonpath_s.format(**variables)

        content_str = json.dumps(content)
        content = json_loads_with_variables(content_str, variables)
    
    return [m.value for m in parse(jsonpath_s).find(content)]