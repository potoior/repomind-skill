"""
RepoMind - 智能项目知识图谱生成工具

扫描代码仓库，提取实体和关系，生成知识图谱
"""

__version__ = "2.0.0"
__author__ = "RepoMind Team"

from .models import KnowledgeGraph, Entity, Relation, EntityType, RelationType
from .knowledge_extractor import KnowledgeExtractor
from .graph_builder import GraphBuilder
from .query_engine import QueryEngine
from .qa_engine import QAEngine
from .flow_analyzer import FlowAnalyzer
from .graph_diff import diff_graphs, GraphDiff
from .graph_merge import merge_graphs, MergeResult

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
]
