import redis
import json
import hashlib


class CacheManager:
    def __init__(self, host='localhost', port=6379, db=0):
        self.r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.ttl = 3600 * 24

    def get(self, key: str) -> dict:
        cached = self.r.get(key)
        return json.loads(cached) if cached else None

    def set(self, key: str, value: dict):
        self.r.setex(key, self.ttl, json.dumps(value))

    def generate_key(self, target_type: str, target_value: str, module: str) -> str:
        hash_input = f"{target_type}:{target_value}:{module}".encode()
        return f"osint:{module}:{hashlib.md5(hash_input).hexdigest()}"