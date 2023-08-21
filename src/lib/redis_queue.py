
import json
from collections import deque
from lib.utils import json_to_byte, byte_to_json

class RedisQueue:
    def __init__(self, r, app, queueid):
        self.r = r
        self.app = app
        self.queueid = queueid
        
    def get_queue(self):
        return f"queue:{self.app.queueid}"
    
    def get_queue_for_query(self, query):
        return f"queue:{self.app.queueid}:{query}"
    
    def peek(self):
        return {}
    
    def peek_query(self):
        return {}
    
    def post_query(self, query, params):
        self.r.lpush(self.get_queue(), query)
        self.r.lpush(self.get_queue_for_query(query), json_to_byte(params))
    
    def pop_queries(self, query, count=1):
        return [byte_to_json(a) for a in self.r.rpop(self.get_queue_for_query(query), count)]
    
    def pop_requests(self, count: int = 1, query=None):
        if query is None:
            queries = self.r.rpop(self.get_queue(), count)
            if queries is None:
                queries = []
                
            qcounts = {q:queries.count(q) for q in set(queries)}
            reqs = {}
            for query,qcount in qcounts.items():
                reqs[query] = deque([self.app.queries[query].apply(params) for params in self.pop_queries(query, qcount)])

            requests = deque()
            for q in queries:
                requests.append(reqs[q].popleft())

            return list(requests), queries
        else:
            count = self.r.lrem(self.get_queue_for_query(query), -count, query)
            requests = [self.app.queries[query].apply(params) for params in self.pop_queries(query, count)]

            return requests, [query]*count