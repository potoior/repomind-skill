import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import KnowledgeGraph, Entity, Relation, EntityType, RelationType
from src.graph_merge import merge_graphs, format_merge_summary, MergeOptions


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
    """创建测试图谱2"""
    return KnowledgeGraph(
        entities=[
            Entity(name="OrderService", type=EntityType.MODULE, description="订单服务", source_file="src/order.py"),
            Entity(name="Database", type=EntityType.DATABASE, description="PostgreSQL"),
            Entity(name="Redis", type=EntityType.TOOL, description="缓存"),
        ],
        relations=[
            Relation(source="OrderService", target="Database", type=RelationType.DEPENDS_ON),
            Relation(source="OrderService", target="Redis", type=RelationType.USES),
        ]
    )


def test_merge_basic():
    """测试基本合并"""
    graph1 = _make_graph_1()
    graph2 = _make_graph_2()
    
    result = merge_graphs([
        ("project1", graph1),
        ("project2", graph2)
    ])
    
    # 应该有4个不同的实体（UserService, Database, FastAPI, OrderService, Redis）
    # Database 重复，应该跳过
    assert len(result.merged_graph.entities) == 5
    assert len(result.merged_graph.relations) == 4
    assert result.entities_skipped == 1  # Database 重复


def test_merge_with_prefix():
    """测试带前缀的合并"""
    graph1 = _make_graph_1()
    graph2 = _make_graph_2()
    
    options = MergeOptions(prefix_project=True)
    result = merge_graphs([
        ("project1", graph1),
        ("project2", graph2)
    ], options)
    
    # 所有实体都应该是唯一的（带前缀）
    assert len(result.merged_graph.entities) == 6
    assert len(result.merged_graph.relations) == 4
    
    # 检查前缀
    names = [e.name for e in result.merged_graph.entities]
    assert "project1.UserService" in names
    assert "project2.OrderService" in names
    assert "project1.Database" in names
    assert "project2.Database" in names


def test_merge_conflict_skip():
    """测试冲突跳过策略"""
    graph1 = KnowledgeGraph(
        entities=[
            Entity(name="Service", type=EntityType.MODULE, description="服务1"),
        ],
        relations=[]
    )
    graph2 = KnowledgeGraph(
        entities=[
            Entity(name="Service", type=EntityType.MODULE, description="服务2"),
        ],
        relations=[]
    )
    
    options = MergeOptions(conflict_strategy='skip')
    result = merge_graphs([
        ("p1", graph1),
        ("p2", graph2)
    ], options)
    
    # 应该跳过重复实体
    assert len(result.merged_graph.entities) == 1
    assert result.entities_skipped == 1
    assert len(result.conflicts) == 1


def test_merge_conflict_overwrite():
    """测试冲突覆盖策略"""
    graph1 = KnowledgeGraph(
        entities=[
            Entity(name="Service", type=EntityType.MODULE, description="服务1"),
        ],
        relations=[]
    )
    graph2 = KnowledgeGraph(
        entities=[
            Entity(name="Service", type=EntityType.MODULE, description="服务2"),
        ],
        relations=[]
    )
    
    options = MergeOptions(conflict_strategy='overwrite')
    result = merge_graphs([
        ("p1", graph1),
        ("p2", graph2)
    ], options)
    
    # 应该覆盖为新实体
    assert len(result.merged_graph.entities) == 1
    assert result.merged_graph.entities[0].description == "服务2"


def test_merge_conflict_keep_both():
    """测试冲突保留两者策略"""
    graph1 = KnowledgeGraph(
        entities=[
            Entity(name="Service", type=EntityType.MODULE, description="服务1"),
        ],
        relations=[]
    )
    graph2 = KnowledgeGraph(
        entities=[
            Entity(name="Service", type=EntityType.MODULE, description="服务2"),
        ],
        relations=[]
    )
    
    options = MergeOptions(conflict_strategy='keep_both')
    result = merge_graphs([
        ("p1", graph1),
        ("p2", graph2)
    ], options)
    
    # 应该保留两个实体
    assert len(result.merged_graph.entities) == 2
    names = [e.name for e in result.merged_graph.entities]
    assert "Service" in names
    assert "Service (p2)" in names


def test_merge_deduplicate_relations():
    """测试关系去重"""
    graph1 = KnowledgeGraph(
        entities=[],
        relations=[
            Relation(source="A", target="B", type=RelationType.USES),
        ]
    )
    graph2 = KnowledgeGraph(
        entities=[],
        relations=[
            Relation(source="A", target="B", type=RelationType.USES),
        ]
    )
    
    options = MergeOptions(deduplicate_relations=True)
    result = merge_graphs([
        ("p1", graph1),
        ("p2", graph2)
    ], options)
    
    # 应该去重
    assert len(result.merged_graph.relations) == 1


def test_merge_statistics():
    """测试合并统计"""
    graph1 = _make_graph_1()
    graph2 = _make_graph_2()
    
    result = merge_graphs([
        ("project1", graph1),
        ("project2", graph2)
    ])
    
    assert len(result.source_projects) == 2
    assert "project1" in result.source_projects
    assert "project2" in result.source_projects


def test_format_merge_summary():
    """测试格式化合并摘要"""
    graph1 = _make_graph_1()
    graph2 = _make_graph_2()
    
    result = merge_graphs([
        ("project1", graph1),
        ("project2", graph2)
    ])
    
    summary = format_merge_summary(result)
    assert "图谱合并摘要" in summary
    assert "project1" in summary
    assert "project2" in summary


def test_merge_empty_graphs():
    """测试空图谱合并"""
    empty = KnowledgeGraph(entities=[], relations=[])
    
    result = merge_graphs([
        ("p1", empty),
        ("p2", empty)
    ])
    
    assert len(result.merged_graph.entities) == 0
    assert len(result.merged_graph.relations) == 0


if __name__ == "__main__":
    test_merge_basic()
    test_merge_with_prefix()
    test_merge_conflict_skip()
    test_merge_conflict_overwrite()
    test_merge_conflict_keep_both()
    test_merge_deduplicate_relations()
    test_merge_statistics()
    test_format_merge_summary()
    test_merge_empty_graphs()
    print("所有 graph_merge 测试通过!")
