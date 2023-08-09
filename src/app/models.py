from pydantic import BaseModel
from typing import Union, Dict

class Request(BaseModel):
    url: str
    method: str = "GET"
    headers: Dict = {}
    data: Dict = {}