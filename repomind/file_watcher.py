"""Watch模式 - 监听文件变化并自动重新分析"""

import os
import time
import hashlib
from pathlib import Path
from typing import Callable, Optional, Dict, Set
from dataclasses import dataclass, field


@dataclass
class FileChangeEvent:
    """文件变更事件"""
    path: str
    change_type: str  # 'created', 'modified', 'deleted'
    timestamp: float


@dataclass
class WatchConfig:
    """监听配置"""
    path: str
    recursive: bool = True
    file_patterns: list = field(default_factory=lambda: ['*.py', '*.js', '*.ts', '*.md', '*.json', '*.yaml', '*.yml'])
    ignore_patterns: list = field(default_factory=lambda: ['__pycache__', '.git', 'node_modules', '.venv', 'venv', 'output', '.mimocode'])
    debounce_seconds: float = 1.0


class FileWatcher:
    """文件监听器"""
    
    def __init__(self, config: WatchConfig, on_change: Callable[[FileChangeEvent], None]):
        self.config = config
        self.on_change = on_change
        self.file_hashes: Dict[str, str] = {}
        self.running = False
        self._last_event_time: Dict[str, float] = {}
    
    def _compute_hash(self, file_path: str) -> Optional[str]:
        """计算文件哈希"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except (OSError, IOError):
            return None
    
    def _should_ignore(self, path: str) -> bool:
        """检查是否应该忽略该路径"""
        path_parts = Path(path).parts
        for ignore in self.config.ignore_patterns:
            if ignore in path_parts:
                return True
        return False
    
    def _matches_pattern(self, file_path: str) -> bool:
        """检查文件是否匹配模式"""
        from fnmatch import fnmatch
        file_name = os.path.basename(file_path)
        for pattern in self.config.file_patterns:
            if fnmatch(file_name, pattern):
                return True
        return False
    
    def _debounce(self, file_path: str) -> bool:
        """防抖检查"""
        now = time.time()
        last_time = self._last_event_time.get(file_path, 0)
        if now - last_time < self.config.debounce_seconds:
            return False
        self._last_event_time[file_path] = now
        return True
    
    def scan_directory(self) -> Dict[str, str]:
        """扫描目录，建立文件哈希索引"""
        file_hashes = {}
        root_path = Path(self.config.path)
        
        if not root_path.exists():
            return file_hashes
        
        if self.config.recursive:
            for root, dirs, files in os.walk(root_path):
                # 过滤忽略的目录
                dirs[:] = [d for d in dirs if not self._should_ignore(os.path.join(root, d))]
                
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    if self._matches_pattern(file_path):
                        file_hash = self._compute_hash(file_path)
                        if file_hash:
                            file_hashes[file_path] = file_hash
        else:
            for item in root_path.iterdir():
                if item.is_file() and self._matches_pattern(str(item)):
                    file_hash = self._compute_hash(str(item))
                    if file_hash:
                        file_hashes[str(item)] = file_hash
        
        return file_hashes
    
    def detect_changes(self) -> list:
        """检测文件变化"""
        changes = []
        current_hashes = self.scan_directory()
        
        # 检测新增和修改
        for file_path, new_hash in current_hashes.items():
            if file_path not in self.file_hashes:
                changes.append(FileChangeEvent(
                    path=file_path,
                    change_type='created',
                    timestamp=time.time()
                ))
            elif self.file_hashes[file_path] != new_hash:
                changes.append(FileChangeEvent(
                    path=file_path,
                    change_type='modified',
                    timestamp=time.time()
                ))
        
        # 检测删除
        for file_path in self.file_hashes:
            if file_path not in current_hashes:
                changes.append(FileChangeEvent(
                    path=file_path,
                    change_type='deleted',
                    timestamp=time.time()
                ))
        
        # 更新哈希索引
        self.file_hashes = current_hashes
        
        return changes
    
    def start(self, callback: Optional[Callable] = None, interval: float = 2.0):
        """开始监听"""
        self.running = True
        self.file_hashes = self.scan_directory()
        
        if callback:
            callback(f"开始监听: {self.config.path}")
            callback(f"监听文件类型: {', '.join(self.config.file_patterns)}")
            callback(f"初始文件数: {len(self.file_hashes)}")
            callback(f"检查间隔: {interval}秒")
            callback("")
        
        try:
            while self.running:
                changes = self.detect_changes()
                
                for change in changes:
                    if self._debounce(change.path):
                        self.on_change(change)
                
                time.sleep(interval)
        except KeyboardInterrupt:
            if callback:
                callback("\n停止监听")
            self.running = False
    
    def stop(self):
        """停止监听"""
        self.running = False


def format_change_event(event: FileChangeEvent) -> str:
    """格式化变更事件"""
    icons = {
        'created': '🟢',
        'modified': '🟡',
        'deleted': '🔴'
    }
    icon = icons.get(event.change_type, '⚪')
    return f"{icon} {event.change_type}: {event.path}"
