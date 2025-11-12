import asyncio
import time
import random
from typing import Optional


class RateLimiter:
    """Rate limiter síncrono y asíncrono"""

    def __init__(self, requests_per_second: float = 2.0):
        self.rate = requests_per_second
        self.tokens = 1.0
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire_async(self):
        """Versión asíncrona"""
        async with self.lock:
            while self.tokens < 1:
                now = time.time()
                elapsed = now - self.last_update
                self.last_update = now
                self.tokens += elapsed * self.rate
                if self.tokens > self.rate:
                    self.tokens = self.rate
                if self.tokens < 1:
                    await asyncio.sleep(0.1)
            self.tokens -= 1

    def acquire_sync(self):
        """Versión síncrona"""
        while self.tokens < 1:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens += elapsed * self.rate
            if self.tokens > self.rate:
                self.tokens = self.rate
            if self.tokens < 1:
                time.sleep(0.1)
        self.tokens -= 1


class AsyncRateLimiter:
    """Rate limiter avanzado para async"""

    def __init__(self, requests_per_second: float):
        self.rate = requests_per_second
        self.tokens = 1.0
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            while self.tokens < 1:
                now = time.time()
                elapsed = now - self.last_update
                self.last_update = now
                self.tokens += elapsed * self.rate
                if self.tokens > self.rate:
                    self.tokens = self.rate
                if self.tokens < 1:
                    await asyncio.sleep(0.1)
            self.tokens -= 1