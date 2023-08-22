from typing import Dict
import base64
import time

from fastapi import FastAPI, HTTPException
import kubernetes as k8s
import redis

from lib.api_key import Key
from lib.models import *
from lib.utils import json_to_byte

app = FastAPI()
k8s.config.load_incluster_config()

r = redis.Redis(host='redis', port=6379, decode_responses=True)

def list_secrets(keyspace):
  # TODO: some k8s code for searching secrets 
  # with keys.qouriers.io/keyspace=={keyspace} , occupying_pod==''
  q = k8s.client.CoreV1Api().list_secret_for_all_namespaces(label_selector=f"keys.qouriers.io/keyspace={keyspace}")
  
  return {s.metadata.name for s in q.items}

def list_keyspaces():
  # list CRD 'keyspaces.keys.qouriers.io'
  q = k8s.client.CustomObjectsApi().list_namespaced_custom_object(group="keys.qouriers.io", 
                                                                  version="v1", 
                                                                  plural="keyspaces", 
                                                                  namespace="qouriers")
  keyspaces = {p['metadata']['name'] for p in q['items']}
  return keyspaces

def get_keyspace(name):
  # list CRD 'keyspaces.keys.qouriers.io'
  q = k8s.client.CustomObjectsApi().get_namespaced_custom_object(group="keys.qouriers.io", 
                                                                  version="v1", 
                                                                  plural="keyspaces", 
                                                                  namespace="qouriers",
                                                                  name=name)
  return q

def on_pod_creation(pod):
  try:
    labels = pod['metadata']['labels']
    keyspace = labels['keys.qouriers.io/keyspace']
  except KeyError:
      return False, "The label key \'keys.qouriers.io/keyspace\' is required", []
    
  keyspaces = list_keyspaces()
  if keyspace not in keyspaces:
    return False, f"The keyspace \'{keyspace}\' does not exist", []

  if labels['app'] == 'qourier-caller':
    patch_obj = []
    keyspace_obj = get_keyspace(keyspace)
    secret = None
    
    if keyspace_obj["spec"]["requires-key"] == True:
      for i in range(5):
        secrets = list_secrets(keyspace)
        if len(secrets) > 0:
          break
        else:
          time.sleep(0.5)
        
      if len(secrets) == 0:
        return False, f"No remaining Secrets left in the keyspace \'{keyspace}\'", []

      secret = list(secrets)[0]
    
      # patch secret
      # TODO: some k8s code to patch the secret
    
    # add volumeMount for every container
    for i, container in enumerate(pod['spec']['containers']):
      # mount secrets
      try: 
        mnt = container["volumeMounts"]
      except KeyError:
        mnt = []
      mnt.append({"name": "qourier-key-secret", "mountPath": "/var/run/secrets/qourier.io"})
      patch_obj.append({"op": "replace", "path": f"/spec/containers/{i}/volumeMounts", "value": mnt})
      
      # mount envs
      try: 
        env = container["env"]
      except KeyError:
        env = []
        
      def replace_or_create_env(name, value):
        env_obj = {"name": name, "value": value}
        try:
          j = [j for j,v in enumerate(env) if v["name"] == name][0]
          env[j] = env_obj
        except IndexError:
          env.append(env_obj)
        
      if "env" in keyspace_obj["spec"].keys():
        keyspace_env = keyspace_obj["spec"]["env"]
        for e in keyspace_env:
          replace_or_create_env(e["name"], e["value"])
        
      if secret is not None:
        replace_or_create_env("KEY_ID", secret)
        
      patch_obj.append({"op": "replace", "path": f"/spec/containers/{i}/env", "value": env})
    
    # add a new volume for mounting secret
    try:
      volumes = pod['spec']['volumes']
    except KeyError:
      volumes = []
    if secret is not None:
      volumes.append({"name": "qourier-key-secret", 
                      "secret": {
                          "secretName": secret
                        }
                      })
    else:
      volumes.append({"name": "qourier-key-secret", 
                "emptyDir": {}
                })
    
    patch_obj.append({"op": "replace", "path": "/spec/volumes", "value": volumes})
    
    return True, "", patch_obj
  
  return True, "", []
  
def on_pod_deletion(pod):
  # if a pod gets deleted, remove 'occupying_pod' label from the secret it occupied
  return True, "", []

def on_secret_creation(secret):
  try:
    labels = secret['metadata']['labels']
    keyspace = labels['keys.qouriers.io/keyspace']
    keyspace_obj = get_keyspace(keyspace)
    
    if "default-limit-rate" in keyspace_obj["spec"].keys():
      lr = keyspace_obj["spec"]["default-limit-rate"]
      lr = {int(k):int(v) for k,v in lr.items()}
      Key(r, secret['metadata']['name']).register(lr)

  except KeyError:
    pass
  return True, "", []

def on_secret_deletion(secret):
  # if a secret gets deleted, delete the pod it was occupying
  Key(r, secret['metadata']['name']).remove()
  
  return True, "", []


# reference : https://coffeewhale.com/kubernetes/admission-control/2021/04/28/opa1/
def validate(review):
  review_obj = review['request']['object']
  
  mapper = {('Pod', 'CREATE'): on_pod_creation,
            ('Pod', 'DELETE'): on_pod_deletion,
            ('Secret', 'CREATE'): on_secret_creation,
            ('Secret', 'DELETE'): on_secret_deletion}
  try:
    return mapper[(review['request']['kind']['kind'], review['request']['operation'])](review_obj)
  
  except KeyError:  # not subject to validation/mutation
    return True, "", []
    
    
@app.post("/")
def root(review: Dict):
    print(review)
    
    result, reason, patch_obj = validate(review)
    if result:
      reason = "Admitted"
      
    admission = {
      "kind": "AdmissionReview",
      "apiVersion": "admission.k8s.io/v1",
      "response": {
        "uid": review['request']['uid'],
        "allowed": result,
        "status": {
          "reason": reason
          }
        }
      }
    
    if len(patch_obj) > 0:
      admission["response"]["patchType"] = "JSONPatch"
      admission["response"]["patch"] = json_to_byte(patch_obj)   # encode with base64
 
    return admission
