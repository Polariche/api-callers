import re
import json
from jsonpath_rw import jsonpath
from jsonpath_rw_ext import parse

varname_regex = '[\w_][\w\d_-]*'
path_regex = '^(\w*://)?((?:[\w\d_-]*\.)*[\w\d_-]*)(?:\:(\d*))?((?:/[\w\d\._-]*)*)'

def path_params_from_url(url):
    return set(re.findall('\{([\w_][\w\d_-]*)\}', url))

def query_params_from_url(url):
    detached_url = re.match(path_regex, url).string
    params = re.findall(f'[\&\?]({varname_regex})=([^\s\&]*)', url)
    return detached_url, dict(params)

def deconstruct_url(url):
    res = {}
    res['protocol'], res['host'], res['port'], res['path'] = re.findall(path_regex, url)[0]
    try:
        res['port'] = int(res['port'])
    except TypeError:
        res['port'] = None

    return res

def apply_path_params(url, params):
    return url.format(**params)

def apply_query_params(url, params):
    url, old_params = query_params_from_url(url)
    old_params.update(params)

    url = url+'?'+'&'.join([f'{k}={v}' for k,v in old_params.items()])

    return url

def json_loads_with_variables(json_string, variables):
    return json.loads(json_string.format(**variables))

def parse_jsonpath_with_variables(jsonpath, content, variables):
    return parse(jsonpath.format(**variables)).find(content.format(**variables))