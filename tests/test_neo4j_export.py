import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from repomind.models import KnowledgeGraph, Entity, Relation, EntityType, RelationType
from repomind.neo4j_export import export_to_neo4j_cypher, export_to_neo4j_json, export_to_neo4j_csv


def _make_test_graph():
    """创建测试图谱"""
    return KnowledgeGraph(
        entities=[
            Entity(name="UserService", type=EntityType.MODULE, description="用户服务"),
            Entity(name="Database", type=EntityType.DATABASE, description="PostgreSQL"),
        ],
        relations=[
            Relation(source="UserService", target="Database", type=RelationType.DEPENDS_ON),
        ]
    )


def test_export_cypher():
    """测试导出为Cypher"""
    graph = _make_test_graph()
    cypher = export_to_neo4j_cypher(graph)
    
    assert "CREATE INDEX" in cypher
    assert "UserService" in cypher
    assert "Database" in cypher
    assert "DEPENDS_ON" in cypher


def test_export_json():
    """测试导出为JSON"""
    graph = _make_test_graph()
    data = export_to_neo4j_json(graph)
    
    assert "nodes" in data
    assert "relationships" in data
    assert len(data["nodes"]) == 2
    assert len(data["relationships"]) == 1


def test_export_csv():
    """测试导出为CSV"""
    import tempfile
    import shutil
    
    graph = _make_test_graph()
    temp_dir = tempfile.mkdtemp()
    
    try:
        result = export_to_neo4j_csv(graph, temp_dir)
        
        assert "nodes_file" in result
        assert "relationships_file" in result
        assert Path(result["nodes_file"]).exists()
        assert Path(result["relationships_file"]).exists()
    finally:
        shutil.rmtree(temp_dir)


def test_cypher_content():
    """测试Cypher内容"""
    graph = _make_test_graph()
    cypher = export_to_neo4j_cypher(graph)
    
    # 检查实体创建
    assert "Module" in cypher
    assert "Database" in cypher
    
    # 检查关系创建
    assert "MATCH" in cypher
    assert "CREATE" in cypher


def test_json_structure():
    """测试JSON结构"""
    graph = _make_test_graph()
    data = export_to_neo4j_json(graph)
    
    # 检查节点结构
    node = data["nodes"][0]
    assert "id" in node
    assert "labels" in node
    assert "properties" in node
    
    # 检查关系结构
    rel = data["relationships"][0]
    assert "type" in rel
    assert "startNode" in rel
    assert "endNode" in rel


if __name__ == "__main__":
    test_export_cypher()
    test_export_json()
    test_export_csv()
    test_cypher_content()
    test_json_structure()
    print("所有 neo4j_export 测试通过!")
