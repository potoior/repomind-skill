import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import KnowledgeGraph, Entity, Relation, EntityType, RelationType
from src.advanced_search import search_entities, SearchOptions, search_with_context, _match_text


def _make_test_graph():
    """创建测试图谱"""
    return KnowledgeGraph(
        entities=[
            Entity(name="UserService", type=EntityType.MODULE, description="用户服务模块，处理用户相关操作", source_file="src/user.py"),
            Entity(name="OrderService", type=EntityType.MODULE, description="订单服务模块", source_file="src/order.py"),
            Entity(name="Database", type=EntityType.DATABASE, description="PostgreSQL数据库"),
            Entity(name="Redis", type=EntityType.TOOL, description="缓存工具"),
            Entity(name="FastAPI", type=EntityType.FRAMEWORK, description="Web框架"),
            Entity(name="README", type=EntityType.DOCUMENT, description="项目文档"),
        ],
        relations=[
            Relation(source="UserService", target="Database", type=RelationType.DEPENDS_ON),
            Relation(source="UserService", target="FastAPI", type=RelationType.USES),
            Relation(source="OrderService", target="Database", type=RelationType.DEPENDS_ON),
            Relation(source="README", target="UserService", type=RelationType.DOCUMENTS),
        ]
    )


def test_search_exact_match():
    """测试精确匹配"""
    graph = _make_test_graph()
    options = SearchOptions(query="UserService")
    results = search_entities(graph, options)
    
    assert len(results) >= 1
    assert results[0].entity.name == "UserService"
    assert results[0].match_type in ['exact', 'contains']


def test_search_contains():
    """测试包含匹配"""
    graph = _make_test_graph()
    options = SearchOptions(query="Service")
    results = search_entities(graph, options)
    
    assert len(results) == 2  # UserService, OrderService
    names = [r.entity.name for r in results]
    assert "UserService" in names
    assert "OrderService" in names


def test_search_case_insensitive():
    """测试不区分大小写"""
    graph = _make_test_graph()
    options = SearchOptions(query="userservice", case_sensitive=False)
    results = search_entities(graph, options)
    
    assert len(results) >= 1
    assert results[0].entity.name == "UserService"


def test_search_case_sensitive():
    """测试区分大小写"""
    graph = _make_test_graph()
    options = SearchOptions(query="userservice", case_sensitive=True)
    results = search_entities(graph, options)
    
    assert len(results) == 0


def test_search_regex():
    """测试正则匹配"""
    graph = _make_test_graph()
    options = SearchOptions(query="^User.*", use_regex=True)
    results = search_entities(graph, options)
    
    assert len(results) >= 1
    assert results[0].entity.name == "UserService"


def test_search_fuzzy():
    """测试模糊匹配"""
    graph = _make_test_graph()
    options = SearchOptions(query="UsrService", fuzzy=True, fuzzy_threshold=0.6)
    results = search_entities(graph, options)
    
    assert len(results) >= 1
    assert results[0].entity.name == "UserService"


def test_search_by_type():
    """测试按类型过滤"""
    graph = _make_test_graph()
    options = SearchOptions(query="Service", entity_types=["Module"])
    results = search_entities(graph, options)
    
    assert len(results) == 2
    for r in results:
        assert r.entity.type == EntityType.MODULE


def test_search_description():
    """测试搜索描述"""
    graph = _make_test_graph()
    options = SearchOptions(query="缓存", search_fields=['description'])
    results = search_entities(graph, options)
    
    assert len(results) >= 1
    assert results[0].entity.name == "Redis"


def test_search_max_results():
    """测试最大结果数"""
    graph = _make_test_graph()
    options = SearchOptions(query="Service", max_results=1)
    results = search_entities(graph, options)
    
    assert len(results) == 1


def test_search_no_results():
    """测试无结果"""
    graph = _make_test_graph()
    options = SearchOptions(query="NonExistent")
    results = search_entities(graph, options)
    
    assert len(results) == 0


def test_match_text_exact():
    """测试文本匹配 - 精确"""
    score, match_type, _ = _match_text("UserService", "UserService", False, False, False, 0.6)
    assert score == 1.0
    assert match_type == 'exact'


def test_match_text_contains():
    """测试文本匹配 - 包含"""
    score, match_type, highlights = _match_text("UserService Module", "Service", False, False, False, 0.6)
    assert score == 0.8
    assert match_type == 'contains'
    assert len(highlights) == 1


def test_match_text_regex():
    """测试文本匹配 - 正则"""
    score, match_type, _ = _match_text("UserService", "^User.*", False, True, False, 0.6)
    assert score == 0.9
    assert match_type == 'regex'


def test_match_text_fuzzy():
    """测试文本匹配 - 模糊"""
    score, match_type, _ = _match_text("UserService", "UsrService", False, False, True, 0.6)
    assert score > 0
    assert match_type == 'fuzzy'


def test_match_text_no_match():
    """测试文本匹配 - 无匹配"""
    score, match_type, _ = _match_text("UserService", "Database", False, False, False, 0.6)
    assert score == 0


def test_search_with_context():
    """测试带上下文的搜索"""
    graph = _make_test_graph()
    result = search_with_context(graph, "UserService")
    
    assert result is not None
    assert result['entity']['name'] == "UserService"
    assert len(result['outgoing']) == 2  # Database, FastAPI
    assert len(result['incoming']) == 1  # README


def test_search_with_context_not_found():
    """测试带上下文的搜索 - 未找到"""
    graph = _make_test_graph()
    result = search_with_context(graph, "NonExistent")
    
    assert result is None


if __name__ == "__main__":
    test_search_exact_match()
    test_search_contains()
    test_search_case_insensitive()
    test_search_case_sensitive()
    test_search_regex()
    test_search_fuzzy()
    test_search_by_type()
    test_search_description()
    test_search_max_results()
    test_search_no_results()
    test_match_text_exact()
    test_match_text_contains()
    test_match_text_regex()
    test_match_text_fuzzy()
    test_match_text_no_match()
    test_search_with_context()
    test_search_with_context_not_found()
    print("所有 advanced_search 测试通过!")
