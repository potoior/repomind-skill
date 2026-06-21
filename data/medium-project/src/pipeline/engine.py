from typing import List, Optional
from dataclasses import dataclass
from ..source.base import Source
from ..transform.base import Transform
from ..sink.base import Sink


@dataclass
class PipelineConfig:
    name: str
    batch_size: int = 1000
    max_retries: int = 3
    timeout: int = 300


class Pipeline:
    """数据管道引擎，负责数据流转和处理。"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.sources: List[Source] = []
        self.transforms: List[Transform] = []
        self.sinks: List[Sink] = []
        self._running = False
    
    def source(self, source: Source) -> 'Pipeline':
        """添加数据源。"""
        self.sources.append(source)
        return self
    
    def transform(self, transform: Transform) -> 'Pipeline':
        """添加转换器。"""
        self.transforms.append(transform)
        return self
    
    def sink(self, sink: Sink) -> 'Pipeline':
        """添加数据输出。"""
        self.sinks.append(sink)
        return self
    
    def run(self) -> None:
        """运行管道。"""
        self._running = True
        for source in self.sources:
            data = source.read()
            for transform in self.transforms:
                data = transform.process(data)
            for sink in self.sinks:
                sink.write(data)
    
    def stop(self) -> None:
        """停止管道。"""
        self._running = False
    
    def get_metrics(self) -> dict:
        """获取管道指标。"""
        return {
            "status": "running" if self._running else "stopped",
            "sources": len(self.sources),
            "transforms": len(self.transforms),
            "sinks": len(self.sinks)
        }