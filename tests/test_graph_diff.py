import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import KnowledgeGraph, Entity, Relation, EntityType, RelationType
from src.graph_diff import diff_graphs, format_diff_summary, format_diff_detail, _entity_key, _relation_key


def _make_graph_1():
    """创建测试图谱1"""
    return KnowledgeGraph(
        entities=[
            Entity(name="UserService", type=EntityType.MODULE, description="用户服务", source_file="src/user.py"),
            Entity(name="Database", type=EntityType.DATABASE, description="PostgreSQL"),
            Entity(name="FastAPI", type=EntityType.FRAMEWORK, description="Web框架"),
        ],
        relations=[
            Relation(source="UserService", target="Database", type=RelationType.DEPENDS_ON),
            Relation(source="UserService", target="FastAPI", type=RelationType.USES),
        ]
    )


def _make_graph_2():
    """创建测试图谱2 (有变更)"""
    return KnowledgeGraph(
        entities=[
            Entity(name="UserService", type=EntityType.MODULE, description="用户服务模块", source_file="src/user.py"),  # 描述修改
            Entity(name="Database", type=EntityType.DATABASE, description="PostgreSQL"),
            Entity(name="Redis", type=EntityType.TOOL, description="缓存"),  # 新增
            # FastAPI 删除
        ],
        relations=[
            Relation(source="UserService", target="Database", type=RelationType.DEPENDS_ON),
            Relation(source="UserService", target="Redis", type=RelationType.USES),  # 新增
            # UserService -> FastAPI 删除
        ]
    )


def test_entity_key():
    """测试实体键生成"""
    entity = Entity(name="Test", type=EntityType.MODULE, description="test")
    assert _entity_key(entity) == "Test|Module"


def test_relation_key():
    """测试关系键生成"""
    relation = Relation(source="A", target="B", type=RelationType.USES)
    assert _relation_key(relation) == "A|B|uses"


def test_diff_no_changes():
    """测试无变更"""
    graph = _make_graph_1()
    diff = diff_graphs(graph, graph)
    
    assert diff.entities_added == 0
    assert diff.entities_deleted == 0
    assert diff.entities_modified == 0
    assert diff.relations_added == 0
    assert diff.relations_deleted == 0


def test_diff_with_changes():
    """测试有变更"""
    old_graph = _make_graph_1()
    new_graph = _make_graph_2()
    
    diff = diff_graphs(old_graph, new_graph)
    
    # UserService 描述修改
    assert diff.entities_modified == 1
    
    # Redis 新增
    assert diff.entities_added == 1
    
    # FastAPI 删除
    assert diff.entities_deleted == 1
    
    # UserService -> Redis 新增
    assert diff.relations_added == 1
    
    # UserService -> FastAPI 删除
    assert diff.relations_deleted == 1


def test_diff_entity_changes_detail():
    """测试实体变更详情"""
    old_graph = _make_graph_1()
    new_graph = _make_graph_2()
    
    diff = diff_graphs(old_graph, new_graph)
    
    # 检查新增实体
    added = [c for c in diff.entity_changes if c.change_type == 'added']
    assert len(added) == 1
    assert added[0].name == "Redis"
    assert added[0].new_type == "Tool"
    
    # 检查删除实体
    deleted = [c for c in diff.entity_changes if c.change_type == 'deleted']
    assert len(deleted) == 1
    assert deleted[0].name == "FastAPI"
    assert deleted[0].old_type == "Framework"
    
    # 检查修改实体
    modified = [c for c in diff.entity_changes if c.change_type == 'modified']
    assert len(modified) == 1
    assert modified[0].name == "UserService"
    assert modified[0].old_description == "用户服务"
    assert modified[0].new_description == "用户服务模块"


def test_diff_relation_changes_detail():
    """测试关系变更详情"""
    old_graph = _make_graph_1()
    new_graph = _make_graph_2()
    
    diff = diff_graphs(old_graph, new_graph)
    
    # 检查新增关系
    added = [c for c in diff.relation_changes if c.change_type == 'added']
    assert len(added) == 1
    assert added[0].source == "UserService"
    assert added[0].target == "Redis"
    
    # 检查删除关系
    deleted = [c for c in diff.relation_changes if c.change_type == 'deleted']
    assert len(deleted) == 1
    assert deleted[0].source == "UserService"
    assert deleted[0].target == "FastAPI"


def test_diff_statistics():
    """测试统计信息"""
    old_graph = _make_graph_1()
    new_graph = _make_graph_2()
    
    diff = diff_graphs(old_graph, new_graph)
    
    assert diff.old_entity_count == 3
    assert diff.new_entity_count == 3
    assert diff.old_relation_count == 2
    assert diff.new_relation_count == 2


def test_format_diff_summary():
    """测试摘要格式化"""
    old_graph = _make_graph_1()
    new_graph = _make_graph_2()
    
    diff = diff_graphs(old_graph, new_graph)
    summary = format_diff_summary(diff)
    
    assert "图谱对比摘要" in summary
    assert "3 → 3" in summary
    assert "+1" in summary
    assert "-1" in summary


def test_format_diff_detail():
    """测试详细格式化"""
    old_graph = _make_graph_1()
    new_graph = _make_graph_2()
    
    diff = diff_graphs(old_graph, new_graph)
    detail = format_diff_detail(diff)
    
    assert "实体变更" in detail
    assert "关系变更" in detail
    assert "Redis" in detail
    assert "FastAPI" in detail
    assert "UserService" in detail


def test_diff_empty_graphs():
    """测试空图谱对比"""
    empty = KnowledgeGraph(entities=[], relations=[])
    
    diff = diff_graphs(empty, empty)
    
    assert diff.entities_added == 0
    assert diff.entities_deleted == 0
    assert diff.relations_added == 0
    assert diff.relations_deleted == 0


if __name__ == "__main__":
    test_entity_key()
    test_relation_key()
    test_diff_no_changes()
    test_diff_with_changes()
    test_diff_entity_changes_detail()
    test_diff_relation_changes_detail()
    test_diff_statistics()
    test_format_diff_summary()
    test_format_diff_detail()
    test_diff_empty_graphs()
    print("所有 graph_diff 测试通过!")
