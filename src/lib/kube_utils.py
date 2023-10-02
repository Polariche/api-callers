
import json 
from jsonpath_rw_ext import parse
import re
import kubernetes as k8s


kube_name_regex = '[a-z0-9][a-z0-9-]*'

kube_query_jsonpath = {
                'name': '$.metadata.name',
                'keyspace': '$.metadata.labels["keys.qouriers.io/keyspace"]',
                'url': '$.spec.url',
                'method': '$.spec.method',
                'input': '$.spec.input',
                'data': '$.spec.data',
                'output': '$.spec.output',
            }
    
def kube_load_query(jsonpath, kube_resource):
    try:
        return parse(jsonpath).find(kube_resource)[0].value
    except IndexError:
        raise AttributeError
    
def kube_find_my_keyspace():
    path = "/etc/podinfo/labels"
    f = open(path, "r")
    keyspace = re.findall(f'keys.qouriers.io/keyspace=\"({kube_name_regex})\"', ''.join(f.readlines()))[0]
    f.close()
    
    return keyspace

def kube_get_queries():
    try:
        k8s.config.load_incluster_config()
        queries = k8s.client.CustomObjectsApi().list_namespaced_custom_object(group="queries.qouriers.io", 
                                                                            version="v1", 
                                                                            plural="apiqueries", 
                                                                            namespace="qouriers")['items']
    
    except:
        with open("/data/apiquery.json") as f:
            queries = json.loads("\n".join(f.readlines()))["items"]
        
    return queries

def kube_get_keyspace(name):
    try:
        k8s.config.load_incluster_config()
        keyspace = k8s.client.CustomObjectsApi().get_namespaced_custom_object(group="keys.qouriers.io", 
                                                                                version="v1", 
                                                                                plural="keyspaces", 
                                                                                namespace="qouriers",
                                                                                name=name)
    except:
        with open("/data/keyspace.json") as f:
            keyspaces = json.loads("\n".join(f.readlines()))["items"]
            found = False
            for keyspace in keyspaces:
                if keyspace["metadata"]["name"] == name:
                    found = True
                    break
    
            if not found:
                raise KeyError()
                
    return keyspace

