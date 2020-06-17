import time


class CachedFile:
    def __init__(self, url, path, timestamp, ttl):
        self.url = url
        self.path = path
        self.timestamp = timestamp
        self.ttl = ttl

    @property
    def is_expired(self):
        now = int(time.time())
        return (now - self.timestamp) > self.ttl

    @classmethod
    def from_dict(cls, cache_dict):
        return cls(
            cache_dict["url"],
            cache_dict["path"],
            cache_dict["timestamp"],
            cache_dict["ttl"],
        )
