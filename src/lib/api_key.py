import os

from lib.utils import flatten_dict, kube_get_keyspace

keyspace = kube_get_keyspace()

class Key:
    def __init__(self, r, key_id):
        self.r = r
        self.key_id = key_id
        self.store_rate_limit = f"rate_limits:{keyspace}:{self.key_id}"
        self.store_rate_limit_count = f"rate_limit_count:{keyspace}:{self.key_id}"
        self.secret = ""
      
    def register(self, rate_limits):
        # rate_limits = {1:20, 120:100}   # seconds:max dict
        self.r.hset(self.store_rate_limit, *flatten_dict(rate_limits))

    def remove(self):
        rate_limits = self.r.hkeys(self.store_rate_limit)

        for seconds in rate_limits:
            self.r.delete(f"{self.store_rate_limit_count}:{seconds}")

        self.r.delete(self.store_rate_limit)

    def use(self):
        rate_limits = self.r.hkeys(self.store_rate_limit)
        rl_map = {}

        for seconds in rate_limits:
            rl_map[seconds] = self.r.incr(f"{self.store_rate_limit_count}:{seconds}")
            self.r.expire(f"{self.store_rate_limit_count}:{seconds}", seconds, "NX")

        return rl_map

    def is_available(self):
        rate_limits = self.get_max()

        for seconds, rl_max in rate_limits.items():
            rate_limit_count = self.r.get(f"{self.store_rate_limit_count}:{seconds}")

            if int(rate_limit_count or 0) >= rl_max:
                waitseconds = self.r.ttl(f"{self.store_rate_limit_count}:{seconds}")
                return False, seconds, waitseconds

        return True, -1, -1

    def get_max(self):
        rate_limits = self.r.hgetall(self.store_rate_limit)
        return {k:int(v or 0) for k,v in rate_limits.items()}

    def get_count(self):
        res = {}
        rate_limits = self.r.hkeys(self.store_rate_limit)
        for seconds in rate_limits:
            res[seconds] = int(self.r.get(f"{self.store_rate_limit_count}:{seconds}") or 0)
            
        return res