import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from repomind.models import KnowledgeGraph, Entity, Relation, EntityType, RelationType


def _make_test_graph():
    """创建测试用的知识图谱"""
    return KnowledgeGraph(
        entities=[
            Entity(name="UserService", type=EntityType.MODULE, description="用户服务模块", source_file="src/user.py"),
            Entity(name="Database", type=EntityType.DATABASE, description="PostgreSQL数据库"),
            Entity(name="FastAPI", type=EntityType.FRAMEWORK, description="Web框架"),
            Entity(name="Redis", type=EntityType.TOOL, description="缓存工具"),
            Entity(name="README", type=EntityType.DOCUMENT, description="项目文档"),
        ],
        relations=[
            Relation(source="UserService", target="Database", type=RelationType.DEPENDS_ON),
            Relation(source="UserService", target="FastAPI", type=RelationType.USES),
            Relation(source="README", target="UserService", type=RelationType.DOCUMENTS),
        ]
    )


def test_show_category():
    """测试分类显示"""
    from cli import _show_category
    from rich.console import Console
    
    graph = _make_test_graph()
    kg = MagicMock()
    kg.current_graph = graph
    
    console = Console(force_terminal=True)
    
    # 测试显示模块
    with patch('cli.console', console):
        _show_category(kg, 'Module', '📦')


def test_show_relations():
    """测试关系显示"""
    from cli import _show_relations
    from rich.console import Console
    
    graph = _make_test_graph()
    kg = MagicMock()
    kg.current_graph = graph
    
    console = Console(force_terminal=True)
    
    with patch('cli.console', console):
        _show_relations(kg, "UserService")


def test_show_dependency_tree():
    """测试依赖树显示"""
    from cli import _show_dependency_tree
    from rich.console import Console
    
    graph = _make_test_graph()
    kg = MagicMock()
    kg.current_graph = graph
    
    console = Console(force_terminal=True)
    
    with patch('cli.console', console):
        _show_dependency_tree(kg, "UserService")


def test_generate_entity_graph():
    """测试实体关系图生成"""
    from cli import _generate_entity_graph
    from rich.console import Console
    
    graph = _make_test_graph()
    kg = MagicMock()
    kg.current_graph = graph
    
    console = Console(force_terminal=True)
    
    with patch('cli.console', console):
        with patch('builtins.open', MagicMock()):
            _generate_entity_graph(kg, "UserService")


def test_show_query_history():
    """测试查询历史显示"""
    from cli import _show_query_history
    from rich.console import Console
    
    console = Console(force_terminal=True)
    
    with patch('cli.console', console):
        _show_query_history(["query1", "query2", "query3"])


def test_show_query_history_empty():
    """测试空查询历史"""
    from cli import _show_query_history
    from rich.console import Console
    
    console = Console(force_terminal=True)
    
    with patch('cli.console', console):
        _show_query_history([])


if __name__ == "__main__":
    test_show_category()
    test_show_relations()
    test_show_dependency_tree()
    test_generate_entity_graph()
    test_show_query_history()
    test_show_query_history_empty()
    print("所有 interactive 测试通过!")
