import os

keyspace = os.environ["KEYSPACE"]

class Key:
    def __init__(self, r, key_id):
        self.r = r
        self.key_id = key_id
        self.secret = ""
      
    def register(self, rate_limits):
        # rate_limits = {1:20, 120:100}   # seconds:max dict
        
        self.r.sadd(f"rate_limits:{keyspace}:{self.key_id}", *rate_limits.keys())

        for seconds, mx in rate_limits.items():
            self.r.set(f"rate_limit_max:{keyspace}:{self.key_id}:{seconds}", mx)

    def remove(self):
        rate_limits = self.r.smembers(f"rate_limits:{self.key_id}")

        for seconds in rate_limits:
            self.r.delete(f"rate_limit_count:{keyspace}:{self.key_id}:{seconds}")
            self.r.delete(f"rate_limit_max:{keyspace}:{self.key_id}:{seconds}")

        self.r.delete(f"rate_limits:{keyspace}:{self.key_id}")

    def use(self):
        rate_limits = self.r.smembers(f"rate_limits:{keyspace}:{self.key_id}")
        rl_map = {}

        for seconds in rate_limits:
            rl_map[seconds] = self.r.incr(f"rate_limit_count:{keyspace}:{self.key_id}:{seconds}")
            self.r.expire(f"rate_limit_count:{keyspace}:{self.key_id}:{seconds}", seconds, "NX")

        return rl_map

    def is_available(self):
        rate_limits = self.r.smembers(f"rate_limits:{keyspace}:{self.key_id}")

        for seconds in rate_limits:
            rate_limit_count = self.r.get(f"rate_limit_count:{keyspace}:{self.key_id}:{seconds}")
            rate_limit_max = self.r.get(f"rate_limit_max:{keyspace}:{self.key_id}:{seconds}")

            if int(rate_limit_count or 0) >= int(rate_limit_max or 0):
                waitseconds = self.r.ttl(f"rate_limit_count:{keyspace}:{self.key_id}:{seconds}")
                return False, seconds, waitseconds

        return True, -1, -1

    def get_max(self):
        res = {}
        rate_limits = self.r.smembers(f"rate_limits:{keyspace}:{self.key_id}")
        for seconds in rate_limits:
            res[seconds] = int(self.r.get(f"rate_limit_max:{keyspace}:{self.key_id}:{seconds}") or 0)

        return res

    def get_count(self):
        res = {}
        rate_limits = self.r.smembers(f"rate_limits:{keyspace}:{self.key_id}")
        for seconds in rate_limits:
            res[seconds] = int(self.r.get(f"rate_limit_count:{keyspace}:{self.key_id}:{seconds}") or 0)
            
        return res