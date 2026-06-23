"""插件系统 - 支持自定义提取器、渲染器、导出格式"""

import os
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .models import KnowledgeGraph, Entity, Relation


class BaseExtractor(ABC):
    """提取器基类"""
    
    @abstractmethod
    def extract(self, file_path: str, content: str) -> tuple:
        """
        从文件内容提取实体和关系
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            (entities, relations) 元组
        """
        pass
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """支持的文件扩展名"""
        pass


class BaseRenderer(ABC):
    """渲染器基类"""
    
    @abstractmethod
    def render(self, graph: KnowledgeGraph, **kwargs) -> str:
        """
        渲染知识图谱
        
        Args:
            graph: 知识图谱
            **kwargs: 额外参数
            
        Returns:
            渲染结果
        """
        pass
    
    @property
    @abstractmethod
    def output_format(self) -> str:
        """输出格式"""
        pass


class BaseExporter(ABC):
    """导出器基类"""
    
    @abstractmethod
    def export(self, graph: KnowledgeGraph, output_path: str) -> str:
        """
        导出知识图谱
        
        Args:
            graph: 知识图谱
            output_path: 输出路径
            
        Returns:
            输出文件路径
        """
        pass
    
    @property
    @abstractmethod
    def format_name(self) -> str:
        """格式名称"""
        pass


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: str  # 'extractor', 'renderer', 'exporter'
    module_path: str
    enabled: bool = True


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugin_dir: str = None):
        self.plugin_dir = plugin_dir or os.path.expanduser("~/.repomind/plugins")
        self.plugins: Dict[str, PluginInfo] = {}
        self.extractors: Dict[str, BaseExtractor] = {}
        self.renderers: Dict[str, BaseRenderer] = {}
        self.exporters: Dict[str, BaseExporter] = {}
        
        # 确保插件目录存在
        Path(self.plugin_dir).mkdir(parents=True, exist_ok=True)
    
    def discover_plugins(self) -> List[PluginInfo]:
        """
        发现插件
        
        Returns:
            插件信息列表
        """
        discovered = []
        
        plugin_path = Path(self.plugin_dir)
        if not plugin_path.exists():
            return discovered
        
        for item in plugin_path.iterdir():
            if item.is_dir():
                plugin_file = item / "plugin.py"
                if plugin_file.exists():
                    try:
                        info = self._load_plugin_info(item.name, plugin_file)
                        if info:
                            discovered.append(info)
                            self.plugins[info.name] = info
                    except Exception as e:
                        print(f"加载插件失败 {item.name}: {e}")
        
        return discovered
    
    def _load_plugin_info(self, name: str, plugin_file: Path) -> Optional[PluginInfo]:
        """加载插件信息"""
        try:
            spec = importlib.util.spec_from_file_location(name, str(plugin_file))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 检查是否有插件元数据
            if hasattr(module, 'PLUGIN_INFO'):
                info = module.PLUGIN_INFO
                return PluginInfo(
                    name=info.get('name', name),
                    version=info.get('version', '1.0.0'),
                    description=info.get('description', ''),
                    author=info.get('author', 'Unknown'),
                    plugin_type=info.get('type', 'unknown'),
                    module_path=str(plugin_file)
                )
            
            # 自动检测插件类型
            plugin_type = None
            if hasattr(module, 'Extractor') and issubclass(module.Extractor, BaseExtractor):
                plugin_type = 'extractor'
            elif hasattr(module, 'Renderer') and issubclass(module.Renderer, BaseRenderer):
                plugin_type = 'renderer'
            elif hasattr(module, 'Exporter') and issubclass(module.Exporter, BaseExporter):
                plugin_type = 'exporter'
            
            if plugin_type:
                return PluginInfo(
                    name=name,
                    version='1.0.0',
                    description=f'{name} plugin',
                    author='Unknown',
                    plugin_type=plugin_type,
                    module_path=str(plugin_file)
                )
            
            return None
            
        except Exception as e:
            print(f"加载插件信息失败 {name}: {e}")
            return None
    
    def load_plugin(self, name: str) -> bool:
        """
        加载插件
        
        Args:
            name: 插件名称
            
        Returns:
            是否加载成功
        """
        if name not in self.plugins:
            return False
        
        info = self.plugins[name]
        
        try:
            spec = importlib.util.spec_from_file_location(name, info.module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 加载提取器
            if hasattr(module, 'Extractor') and issubclass(module.Extractor, BaseExtractor):
                self.extractors[name] = module.Extractor()
            
            # 加载渲染器
            if hasattr(module, 'Renderer') and issubclass(module.Renderer, BaseRenderer):
                self.renderers[name] = module.Renderer()
            
            # 加载导出器
            if hasattr(module, 'Exporter') and issubclass(module.Exporter, BaseExporter):
                self.exporters[name] = module.Exporter()
            
            info.enabled = True
            return True
            
        except Exception as e:
            print(f"加载插件失败 {name}: {e}")
            return False
    
    def load_all_plugins(self):
        """加载所有发现的插件"""
        self.discover_plugins()
        for name in self.plugins:
            self.load_plugin(name)
    
    def get_extractor(self, name: str) -> Optional[BaseExtractor]:
        """获取提取器"""
        return self.extractors.get(name)
    
    def get_renderer(self, name: str) -> Optional[BaseRenderer]:
        """获取渲染器"""
        return self.renderers.get(name)
    
    def get_exporter(self, name: str) -> Optional[BaseExporter]:
        """获取导出器"""
        return self.exporters.get(name)
    
    def list_plugins(self) -> List[Dict]:
        """列出所有插件"""
        plugins = []
        for name, info in self.plugins.items():
            plugins.append({
                'name': info.name,
                'version': info.version,
                'description': info.description,
                'type': info.plugin_type,
                'enabled': info.enabled
            })
        return plugins
    
    def extract_with_plugins(self, file_path: str, content: str) -> tuple:
        """
        使用插件提取知识
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            (entities, relations) 元组
        """
        ext = Path(file_path).suffix.lower()
        
        all_entities = []
        all_relations = []
        
        for name, extractor in self.extractors.items():
            if ext in extractor.supported_extensions:
                try:
                    entities, relations = extractor.extract(file_path, content)
                    all_entities.extend(entities)
                    all_relations.extend(relations)
                except Exception as e:
                    print(f"插件 {name} 提取失败: {e}")
        
        return all_entities, all_relations
    
    def render_with_plugin(self, name: str, graph: KnowledgeGraph, **kwargs) -> Optional[str]:
        """
        使用插件渲染
        
        Args:
            name: 插件名称
            graph: 知识图谱
            **kwargs: 额外参数
            
        Returns:
            渲染结果
        """
        renderer = self.get_renderer(name)
        if renderer:
            return renderer.render(graph, **kwargs)
        return None
    
    def export_with_plugin(self, name: str, graph: KnowledgeGraph, output_path: str) -> Optional[str]:
        """
        使用插件导出
        
        Args:
            name: 插件名称
            graph: 知识图谱
            output_path: 输出路径
            
        Returns:
            输出文件路径
        """
        exporter = self.get_exporter(name)
        if exporter:
            return exporter.export(graph, output_path)
        return None


# 全局插件管理器实例
_plugin_manager = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def create_plugin_template(plugin_name: str, plugin_type: str, output_dir: str = None):
    """
    创建插件模板
    
    Args:
        plugin_name: 插件名称
        plugin_type: 插件类型 ('extractor', 'renderer', 'exporter')
        output_dir: 输出目录
    """
    if output_dir is None:
        output_dir = os.path.expanduser(f"~/.repomind/plugins/{plugin_name}")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 生成插件代码
    if plugin_type == 'extractor':
        code = '''"""自定义提取器插件"""

from repomind.plugin_system import BaseExtractor
from repomind.models import Entity, Relation, EntityType, RelationType


PLUGIN_INFO = {
    'name': '{name}',
    'version': '1.0.0',
    'description': '自定义提取器',
    'author': 'Your Name',
    'type': 'extractor'
}


class Extractor(BaseExtractor):
    """自定义提取器"""
    
    @property
    def supported_extensions(self):
        return ['.py', '.js']  # 修改为支持的扩展名
    
    def extract(self, file_path: str, content: str):
        """提取实体和关系"""
        entities = []
        relations = []
        
        # 在这里实现提取逻辑
        # 示例: 提取类定义
        import re
        for match in re.finditer(r'class\\s+(\\w+)', content):
            entities.append(Entity(
                name=match.group(1),
                type=EntityType.MODULE,
                description=f'类: {match.group(1)}',
                source_file=file_path
            ))
        
        return entities, relations
'''.format(name=plugin_name)
    
    elif plugin_type == 'renderer':
        code = '''"""自定义渲染器插件"""

from repomind.plugin_system import BaseRenderer
from repomind.models import KnowledgeGraph


PLUGIN_INFO = {
    'name': '{name}',
    'version': '1.0.0',
    'description': '自定义渲染器',
    'author': 'Your Name',
    'type': 'renderer'
}


class Renderer(BaseRenderer):
    """自定义渲染器"""
    
    @property
    def output_format(self):
        return 'html'  # 修改为输出格式
    
    def render(self, graph: KnowledgeGraph, **kwargs):
        """渲染知识图谱"""
        # 在这里实现渲染逻辑
        html = '<html><body>'
        html += f'<h1>实体: {len(graph.entities)}</h1>'
        html += f'<h1>关系: {len(graph.relations)}</h1>'
        html += '</body></html>'
        return html
'''.format(name=plugin_name)
    
    elif plugin_type == 'exporter':
        code = '''"""自定义导出器插件"""

from repomind.plugin_system import BaseExporter
from repomind.models import KnowledgeGraph


PLUGIN_INFO = {
    'name': '{name}',
    'version': '1.0.0',
    'description': '自定义导出器',
    'author': 'Your Name',
    'type': 'exporter'
}


class Exporter(BaseExporter):
    """自定义导出器"""
    
    @property
    def format_name(self):
        return 'custom'  # 修改为格式名称
    
    def export(self, graph: KnowledgeGraph, output_path: str):
        """导出知识图谱"""
        # 在这里实现导出逻辑
        with open(output_path, 'w') as f:
            f.write(f'Entities: {len(graph.entities)}\\n')
            f.write(f'Relations: {len(graph.relations)}\\n')
        return output_path
'''.format(name=plugin_name)
    
    else:
        raise ValueError(f"未知的插件类型: {plugin_type}")
    
    # 写入文件
    plugin_file = output_path / "plugin.py"
    with open(plugin_file, 'w', encoding='utf-8') as f:
        f.write(code)
    
    # 写入README
    readme = f"""# {plugin_name}

类型: {plugin_type}
版本: 1.0.0

## 安装

将此目录复制到 `~/.repomind/plugins/` 目录下。

## 使用

插件会自动被 RepoMind 加载。
"""
    
    readme_file = output_path / "README.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme)
    
    return str(plugin_file)
