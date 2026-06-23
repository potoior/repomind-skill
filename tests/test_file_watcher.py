import sys
import os
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.file_watcher import FileWatcher, WatchConfig, FileChangeEvent, format_change_event


def _create_temp_dir():
    """创建临时目录"""
    return tempfile.mkdtemp()


def _create_temp_file(dir_path, content="test content"):
    """创建临时文件"""
    import random
    file_path = os.path.join(dir_path, f"test_{random.randint(1000, 9999)}.py")
    with open(file_path, 'w') as f:
        f.write(content)
    return file_path


def test_watch_config_defaults():
    """测试默认配置"""
    config = WatchConfig(path="/tmp")
    assert config.recursive is True
    assert '*.py' in config.file_patterns
    assert '__pycache__' in config.ignore_patterns


def test_file_watcher_scan():
    """测试文件扫描"""
    temp_dir = _create_temp_dir()
    try:
        # 创建测试文件
        _create_temp_file(temp_dir, "content1")
        _create_temp_file(temp_dir, "content2")
        
        config = WatchConfig(path=temp_dir)
        watcher = FileWatcher(config, lambda e: None)
        
        files = watcher.scan_directory()
        assert len(files) == 2
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_file_watcher_detect_created():
    """测试检测新增文件"""
    temp_dir = _create_temp_dir()
    try:
        config = WatchConfig(path=temp_dir)
        watcher = FileWatcher(config, lambda e: None)
        
        # 初始扫描
        watcher.file_hashes = watcher.scan_directory()
        assert len(watcher.file_hashes) == 0
        
        # 创建新文件
        _create_temp_file(temp_dir)
        
        # 检测变更
        changes = watcher.detect_changes()
        assert len(changes) == 1
        assert changes[0].change_type == 'created'
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_file_watcher_detect_modified():
    """测试检测修改文件"""
    temp_dir = _create_temp_dir()
    try:
        # 创建测试文件
        file_path = _create_temp_file(temp_dir, "original")
        
        config = WatchConfig(path=temp_dir)
        watcher = FileWatcher(config, lambda e: None)
        
        # 初始扫描
        watcher.file_hashes = watcher.scan_directory()
        assert len(watcher.file_hashes) == 1
        
        # 修改文件
        with open(file_path, 'w') as f:
            f.write("modified")
        
        # 检测变更
        changes = watcher.detect_changes()
        assert len(changes) == 1
        assert changes[0].change_type == 'modified'
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_file_watcher_detect_deleted():
    """测试检测删除文件"""
    temp_dir = _create_temp_dir()
    try:
        # 创建测试文件
        file_path = _create_temp_file(temp_dir)
        
        config = WatchConfig(path=temp_dir)
        watcher = FileWatcher(config, lambda e: None)
        
        # 初始扫描
        watcher.file_hashes = watcher.scan_directory()
        assert len(watcher.file_hashes) == 1
        
        # 删除文件
        os.remove(file_path)
        
        # 检测变更
        changes = watcher.detect_changes()
        assert len(changes) == 1
        assert changes[0].change_type == 'deleted'
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_file_watcher_no_changes():
    """测试无变更"""
    temp_dir = _create_temp_dir()
    try:
        # 创建测试文件
        _create_temp_file(temp_dir)
        
        config = WatchConfig(path=temp_dir)
        watcher = FileWatcher(config, lambda e: None)
        
        # 初始扫描
        watcher.file_hashes = watcher.scan_directory()
        
        # 再次扫描（无变更）
        changes = watcher.detect_changes()
        assert len(changes) == 0
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_file_watcher_ignore_patterns():
    """测试忽略模式"""
    temp_dir = _create_temp_dir()
    try:
        # 创建忽略的目录和文件
        ignore_dir = os.path.join(temp_dir, '__pycache__')
        os.makedirs(ignore_dir)
        _create_temp_file(ignore_dir)
        
        # 创建正常文件
        _create_temp_file(temp_dir)
        
        config = WatchConfig(path=temp_dir)
        watcher = FileWatcher(config, lambda e: None)
        
        files = watcher.scan_directory()
        # 只有正常目录下的文件，__pycache__下的应该被忽略
        assert len(files) == 1
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_format_change_event():
    """测试格式化变更事件"""
    event = FileChangeEvent(
        path="/tmp/test.py",
        change_type='modified',
        timestamp=time.time()
    )
    
    formatted = format_change_event(event)
    assert 'modified' in formatted
    assert '/tmp/test.py' in formatted


def test_file_watcher_stop():
    """测试停止监听"""
    temp_dir = _create_temp_dir()
    try:
        config = WatchConfig(path=temp_dir)
        watcher = FileWatcher(config, lambda e: None)
        
        assert watcher.running is False
        watcher.running = True
        watcher.stop()
        assert watcher.running is False
    finally:
        import shutil
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_watch_config_defaults()
    test_file_watcher_scan()
    test_file_watcher_detect_created()
    test_file_watcher_detect_modified()
    test_file_watcher_detect_deleted()
    test_file_watcher_no_changes()
    test_file_watcher_ignore_patterns()
    test_format_change_event()
    test_file_watcher_stop()
    print("所有 file_watcher 测试通过!")
