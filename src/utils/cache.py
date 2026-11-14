import os
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import logging
import time

class CacheManager:
    """
    Enterprise caching system
    
    Features:
    - Memory and disk caching
    - TTL management
    - Automatic cleanup
    - Hit/miss tracking
    """
    
    def __init__(self, config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        self.cache_dir = config.get('data.cache_directory', 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.memory_cache = {}
        self.stats = {'hits': 0, 'misses': 0}
        
        self.logger.info("Cache manager initialized")
    
    def _generate_key(self, key: str) -> str:
        """Generate cache key hash"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, key: str, max_age_seconds: int = 3600) -> Optional[Any]:
        """
        Get from cache if not expired
        
        Args:
            key: Cache key
            max_age_seconds: Maximum age in seconds
        
        Returns:
            Cached value or None
        """
        cache_key = self._generate_key(key)
        
        # Check memory cache
        if cache_key in self.memory_cache:
            data, timestamp = self.memory_cache[cache_key]
            age = (datetime.now() - timestamp).total_seconds()
            
            if age < max_age_seconds:
                self.stats['hits'] += 1
                self.logger.debug(f"Cache hit (memory): {key}")
                return data
        
        # Check disk cache
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        if os.path.exists(cache_file):
            file_age = time.time() - os.path.getmtime(cache_file)
            
            if file_age < max_age_seconds:
                try:
                    with open(cache_file, 'rb', encoding="utf-8") as f:
                        data = pickle.load(f)
                    
                    # Update memory cache
                    self.memory_cache[cache_key] = (data, datetime.now())
                    
                    self.stats['hits'] += 1
                    self.logger.debug(f"Cache hit (disk): {key}")
                    return data
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load cache {key}: {e}")
        
        self.stats['misses'] += 1
        return None
    
    def set(self, key: str, data: Any):
        """
        Save to cache
        
        Args:
            key: Cache key
            data: Data to cache
        """
        cache_key = self._generate_key(key)
        
        # Save to memory
        self.memory_cache[cache_key] = (data, datetime.now())
        
        # Save to disk
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        try:
            with open(cache_file, 'wb', encoding="utf-8") as f:
                pickle.dump(data, f)
            
            self.logger.debug(f"Cached: {key}")
            
        except Exception as e:
            self.logger.warning(f"Failed to cache {key}: {e}")
    
    def invalidate(self, pattern: str = None):
        """
        Invalidate cache entries
        
        Args:
            pattern: Pattern to match (None = clear all)
        """
        if pattern:
            # Invalidate matching keys
            keys_to_remove = [
                k for k in self.memory_cache.keys() 
                if pattern in k
            ]
            
            for key in keys_to_remove:
                del self.memory_cache[key]
                
                cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            
            self.logger.info(f"Invalidated {len(keys_to_remove)} cache entries")
            
        else:
            # Clear all
            self.memory_cache.clear()
            
            for file in os.listdir(self.cache_dir):
                os.remove(os.path.join(self.cache_dir, file))
            
            self.logger.info("Cleared all cache")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total if total > 0 else 0
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': f"{hit_rate*100:.2f}%",
            'memory_cache_size': len(self.memory_cache)
        }
