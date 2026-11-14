import time
from collections import deque
from threading import Lock
from typing import Dict

class RateLimiter:
    """
    Token bucket rate limiter
    
    Features:
    - Smooth rate limiting
    - Burst handling
    - Thread-safe
    - Statistics tracking
    """
    
    def __init__(self, calls_per_minute: int = 100, burst_size: int = 10):
        """
        Initialize rate limiter
        
        Args:
            calls_per_minute: Maximum calls per minute
            burst_size: Maximum burst size
        """
        self.calls_per_minute = calls_per_minute
        self.burst_size = burst_size
        self.tokens = float(burst_size)
        self.last_update = time.time()
        self.lock = Lock()
        
        # Statistics
        self.call_times = deque(maxlen=1000)
        self.total_calls = 0
        self.total_wait_time = 0
    
    def acquire(self):
        """
        Acquire permission to make a call
        Blocks if rate limit would be exceeded
        """
        with self.lock:
            now = time.time()
            
            # Refill tokens based on time passed
            time_passed = now - self.last_update
            self.tokens += time_passed * (self.calls_per_minute / 60.0)
            self.tokens = min(self.tokens, self.burst_size)
            self.last_update = now
            
            # Wait if no tokens available
            wait_time = 0
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / (self.calls_per_minute / 60.0)
                time.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1
            
            # Track statistics
            self.call_times.append(now)
            self.total_calls += 1
            self.total_wait_time += wait_time
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        now = time.time()
        recent_calls = [t for t in self.call_times if now - t < 60]
        
        return {
            'calls_last_minute': len(recent_calls),
            'rate_limit': self.calls_per_minute,
            'available_tokens': int(self.tokens),
            'utilization': f"{len(recent_calls)/self.calls_per_minute*100:.1f}%",
            'total_calls': self.total_calls,
            'avg_wait_time': f"{self.total_wait_time/max(1, self.total_calls):.3f}s"
        }

