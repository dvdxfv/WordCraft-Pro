"""长文处理性能优化模块

核心优化策略：
1. 文档分块处理（Chunking）- 将大文档分成小块并行处理
2. 增量解析（Incremental）- 只处理修改部分
3. 异步检查（Async）- 不阻塞编辑
4. 缓存机制（Caching）- 避免重复计算
5. 内存优化（Memory）- 自动释放未使用数据

性能目标：
- 5 千字：≤4 秒，≤128MB
- 1 万字：≤8 秒，≤256MB
- 2 万字：≤15 秒，≤384MB
- 5 万字：≤30 秒，≤512MB
"""

import hashlib
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
import threading


@dataclass
class Chunk:
    """文档分块"""
    chunk_id: str
    start_index: int
    end_index: int
    content_hash: str
    elements: List = field(default_factory=list)
    is_modified: bool = True
    last_check_time: float = 0.0


@dataclass
class CheckResult:
    """检查结果缓存"""
    chunk_id: str
    issues: List
    check_time: float
    is_valid: bool = True


class LRUCache:
    """LRU 缓存（基于 OrderedDict 实现）"""
    
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[any]:
        with self.lock:
            if key not in self.cache:
                return None
            # 移动到末尾（最近使用）
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def put(self, key: str, value: any):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            # 超出容量则移除最旧的
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
    
    def clear(self):
        with self.lock:
            self.cache.clear()


class DocumentChunker:
    """文档分块器"""
    
    def __init__(self, chunk_size: int = 1000):
        """
        Args:
            chunk_size: 每个分块的最大元素数量
        """
        self.chunk_size = chunk_size
    
    def chunk(self, elements: List, content_hash: str = None) -> List[Chunk]:
        """将文档元素分块"""
        chunks = []
        total = len(elements)
        
        for i in range(0, total, self.chunk_size):
            chunk_elements = elements[i:i + self.chunk_size]
            chunk_content = "".join([elem.text or "" for elem in chunk_elements])
            chunk_hash = hashlib.md5(chunk_content.encode()).hexdigest()
            
            chunk = Chunk(
                chunk_id=f"chunk_{i // self.chunk_size}",
                start_index=i,
                end_index=min(i + self.chunk_size, total),
                content_hash=chunk_hash,
                elements=chunk_elements,
                is_modified=True,
            )
            chunks.append(chunk)
        
        return chunks
    
    def update_chunks(self, chunks: List[Chunk], new_elements: List, 
                     old_hash_map: Dict[str, str]) -> List[Chunk]:
        """更新分块（只标记修改的分块）"""
        new_chunks = self.chunk(new_elements)
        
        # 对比哈希值，标记未修改的分块
        for chunk in new_chunks:
            old_hash = old_hash_map.get(chunk.chunk_id)
            if old_hash and old_hash == chunk.content_hash:
                chunk.is_modified = False
        
        return new_chunks


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self, chunk_size: int = 1000, cache_size: int = 50):
        """
        Args:
            chunk_size: 分块大小
            cache_size: 缓存容量
        """
        self.chunker = DocumentChunker(chunk_size)
        self.result_cache = LRUCache(cache_size)
        self.chunk_hash_map: Dict[str, str] = {}
        self.check_timestamps: Dict[str, float] = {}
        self.lock = threading.Lock()
        
        # 性能统计
        self.stats = {
            'total_checks': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
        }
    
    def prepare_chunks(self, elements: List) -> List[Chunk]:
        """准备分块（首次全量，后续增量）"""
        chunks = self.chunker.chunk(elements)
        
        # 更新哈希映射
        with self.lock:
            for chunk in chunks:
                self.chunk_hash_map[chunk.chunk_id] = chunk.content_hash
        
        return chunks
    
    def get_modified_chunks(self, chunks: List[Chunk], 
                           new_elements: List) -> Tuple[List[Chunk], Dict[str, str]]:
        """获取修改的分块"""
        # 重新分块
        new_chunks = self.chunker.update_chunks(
            chunks, new_elements, self.chunk_hash_map
        )
        
        # 更新哈希映射
        with self.lock:
            for chunk in new_chunks:
                self.chunk_hash_map[chunk.chunk_id] = chunk.content_hash
        
        # 只返回修改的分块
        modified_chunks = [c for c in new_chunks if c.is_modified]
        
        return modified_chunks, new_chunks
    
    def cache_result(self, chunk_id: str, issues: List, check_time: float):
        """缓存检查结果"""
        result = CheckResult(
            chunk_id=chunk_id,
            issues=issues,
            check_time=check_time,
            is_valid=True
        )
        self.result_cache.put(chunk_id, result)
        self.stats['total_checks'] += 1
        self.stats['total_time'] += check_time
        self.stats['avg_time'] = self.stats['total_time'] / self.stats['total_checks']
    
    def get_cached_result(self, chunk_id: str) -> Optional[CheckResult]:
        """获取缓存的检查结果"""
        result = self.result_cache.get(chunk_id)
        if result:
            self.stats['cache_hits'] += 1
        else:
            self.stats['cache_misses'] += 1
        return result
    
    def invalidate_cache(self, chunk_ids: List[str] = None):
        """使缓存失效"""
        if chunk_ids:
            for chunk_id in chunk_ids:
                result = self.result_cache.get(chunk_id)
                if result:
                    result.is_valid = False
        else:
            self.result_cache.clear()
    
    def get_performance_report(self) -> Dict:
        """获取性能报告"""
        cache_hit_rate = (
            self.stats['cache_hits'] / 
            (self.stats['cache_hits'] + self.stats['cache_misses'])
            if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0
            else 0.0
        )
        
        return {
            'total_checks': self.stats['total_checks'],
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'cache_hit_rate': f"{cache_hit_rate:.2%}",
            'total_time_sec': f"{self.stats['total_time']:.2f}",
            'avg_time_sec': f"{self.stats['avg_time']:.3f}",
            'cached_chunks': len(self.chunk_hash_map),
        }


class AsyncChecker:
    """异步检查器（模拟异步，实际在 Web 端使用 Web Worker）"""
    
    def __init__(self, optimizer: PerformanceOptimizer):
        self.optimizer = optimizer
        self.is_running = False
        self.pending_chunks: List[Chunk] = []
        self.results: Dict[str, List] = {}
    
    def start_check(self, chunks: List[Chunk], check_func):
        """开始异步检查"""
        self.pending_chunks = chunks
        self.is_running = True
        self.results = {}
        
        # 在后台线程中执行检查
        thread = threading.Thread(target=self._run_check, args=(check_func,))
        thread.daemon = True
        thread.start()
    
    def _run_check(self, check_func):
        """执行检查（后台线程）"""
        for chunk in self.pending_chunks:
            if not self.is_running:
                break
            
            # 检查缓存
            cached = self.optimizer.get_cached_result(chunk.chunk_id)
            if cached and cached.is_valid:
                self.results[chunk.chunk_id] = cached.issues
                continue
            
            # 执行实际检查
            start_time = time.time()
            issues = check_func(chunk.elements)
            check_time = time.time() - start_time
            
            # 缓存结果
            self.optimizer.cache_result(chunk.chunk_id, issues, check_time)
            self.results[chunk.chunk_id] = issues
        
        self.is_running = False
    
    def stop(self):
        """停止检查"""
        self.is_running = False
    
    def get_results(self) -> Dict[str, List]:
        """获取检查结果"""
        return self.results


# 全局优化器实例（单例模式）
_global_optimizer: Optional[PerformanceOptimizer] = None
_global_async_checker: Optional[AsyncChecker] = None


def get_optimizer(chunk_size: int = 1000, cache_size: int = 50) -> PerformanceOptimizer:
    """获取全局优化器实例"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = PerformanceOptimizer(chunk_size, cache_size)
    return _global_optimizer


def get_async_checker() -> AsyncChecker:
    """获取全局异步检查器"""
    global _global_async_checker
    if _global_async_checker is None:
        _global_async_checker = AsyncChecker(get_optimizer())
    return _global_async_checker
