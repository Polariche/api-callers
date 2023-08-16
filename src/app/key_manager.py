from fastapi import FastAPI, HTTPException
from typing import Dict
import kubernetes as k8s

from lib.models import *

app = FastAPI()

# reference : https://coffeewhale.com/kubernetes/admission-control/2021/04/28/opa1/
def validate(review):
    # denying all Pod creating
    """
    if (review['request']['object']['kind'] == 'Pod') and \
        (review['request']['operation'] == 'CREATE'):
        return False  # Deny
    return True       # Accept
    """
    
@app.post("/")
def root(review: Dict):
    print(review)
    #result = validate(review)
 
    return {
      "kind": "AdmissionReview",
      "apiVersion": "admission.k8s.io/v1",
      "response": {
        "uid": review['request']['uid'],
        "allowed": False,
        "status": {
          "reason": "Pod create not allowed"
        },
        #"patchType": "JSONPatch",
        #"patch": "W3tvcDogYWRkLCBwYXRoOiAvbWV0YWRhdGEvYW5ub3RhdGlvbnMvZm9vLCB2YWx1ZTogYmFyfV0="
      }
    }
