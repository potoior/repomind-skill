from abc import ABC, abstractmethod
from typing import Iterator, Any, Callable


class Transform(ABC):
    """转换器基类。"""
    
    @abstractmethod
    def process(self, data: Iterator[Any]) -> Iterator[Any]:
        """处理数据。"""
        pass


class Map(Transform):
    """映射转换器。"""
    
    def __init__(self, func: Callable):
        self.func = func
    
    def process(self, data: Iterator[Any]) -> Iterator[Any]:
        for item in data:
            yield self.func(item)


class Filter(Transform):
    """过滤转换器。"""
    
    def __init__(self, predicate: Callable):
        self.predicate = predicate
    
    def process(self, data: Iterator[Any]) -> Iterator[Any]:
        for item in data:
            if self.predicate(item):
                yield item


class FlatMap(Transform):
    """扁平化转换器。"""
    
    def __init__(self, func: Callable):
        self.func = func
    
    def process(self, data: Iterator[Any]) -> Iterator[Any]:
        for item in data:
            yield from self.func(item)


class Aggregate(Transform):
    """聚合转换器。"""
    
    def __init__(self, key_func: Callable, agg_func: Callable):
        self.key_func = key_func
        self.agg_func = agg_func
    
    def process(self, data: Iterator[Any]) -> Iterator[Any]:
        groups = {}
        for item in data:
            key = self.key_func(item)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        for key, group in groups.items():
            yield self.agg_func(group)