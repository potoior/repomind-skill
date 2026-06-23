"""
RepoMind - 智能项目知识图谱生成工具

扫描代码仓库，提取实体和关系，生成知识图谱
"""

__version__ = "2.1.0"
__author__ = "RepoMind Team"

from .models import KnowledgeGraph, Entity, Relation, EntityType, RelationType
from .knowledge_extractor import KnowledgeExtractor
from .graph_builder import GraphBuilder
from .query_engine import QueryEngine
from .qa_engine import QAEngine
from .flow_analyzer import FlowAnalyzer
from .graph_diff import diff_graphs, GraphDiff
from .graph_merge import merge_graphs, MergeResult

# 新增模块 (懒加载)
def __getattr__(name):
    if name == 'github_integration':
        from . import github_integration
        return github_integration
    elif name == 'neo4j_export':
        from . import neo4j_export
        return neo4j_export
    elif name == 'git_history':
        from . import git_history
        return git_history
    elif name == 'parallel_extractor':
        from . import parallel_extractor
        return parallel_extractor
    elif name == 'plugin_system':
        from . import plugin_system
        return plugin_system
    raise AttributeError(f"module 'repomind' has no attribute {name}")

__all__ = [
    "KnowledgeGraph",
    "Entity",
    "Relation",
    "EntityType",
    "RelationType",
    "KnowledgeExtractor",
    "GraphBuilder",
    "QueryEngine",
    "QAEngine",
    "FlowAnalyzer",
    "diff_graphs",
    "GraphDiff",
    "merge_graphs",
    "MergeResult",
    "github_integration",
    "neo4j_export",
    "git_history",
    "parallel_extractor",
    "plugin_system",
]
