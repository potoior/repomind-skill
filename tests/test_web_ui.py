import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from repomind.web_ui import create_app, set_output_dir, _state
from repomind.models import KnowledgeGraph, Entity, Relation, EntityType, RelationType
from repomind.graph_builder import GraphBuilder
import tempfile
import os


def _create_test_graph():
    """创建测试图谱"""
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


def _setup_test_data():
    """设置测试数据"""
    # 重置状态
    _state["graphs"] = {}
    _state["current_graph"] = None
    _state["current_name"] = None
    
    temp_dir = tempfile.mkdtemp()
    graph = _create_test_graph()
    builder = GraphBuilder(temp_dir)
    builder.save_graph(graph, "test-project")
    set_output_dir(temp_dir)
    return temp_dir


def test_list_projects():
    """测试列出项目"""
    temp_dir = _setup_test_data()
    try:
        app = create_app(temp_dir)
        client = TestClient(app)
        
        response = client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert len(data["projects"]) > 0
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_get_project():
    """测试获取项目详情"""
    temp_dir = _setup_test_data()
    try:
        app = create_app(temp_dir)
        client = TestClient(app)
        
        response = client.get("/api/projects/test-project")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-project"
        assert data["entities"] == 3
        assert data["relations"] == 2
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_search():
    """测试搜索"""
    temp_dir = _setup_test_data()
    try:
        app = create_app(temp_dir)
        client = TestClient(app)
        
        response = client.post("/api/search", json={"query": "User"})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0
        assert data["results"][0]["name"] == "UserService"
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_get_entity():
    """测试获取实体详情"""
    temp_dir = _setup_test_data()
    try:
        app = create_app(temp_dir)
        client = TestClient(app)
        
        response = client.get("/api/entity/UserService")
        assert response.status_code == 200
        data = response.json()
        assert data["entity"]["name"] == "UserService"
        assert len(data["outgoing"]) == 2
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_get_entity_not_found():
    """测试获取不存在的实体"""
    temp_dir = _setup_test_data()
    try:
        app = create_app(temp_dir)
        client = TestClient(app)
        
        response = client.get("/api/entity/NonExistent")
        assert response.status_code == 404
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_list_entities():
    """测试列出实体"""
    temp_dir = _setup_test_data()
    try:
        app = create_app(temp_dir)
        client = TestClient(app)
        
        response = client.get("/api/entities")
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert data["total"] == 3
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_list_entities_by_type():
    """测试按类型列出实体"""
    temp_dir = _setup_test_data()
    try:
        app = create_app(temp_dir)
        client = TestClient(app)
        
        response = client.get("/api/entities?type=Module")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["entities"][0]["name"] == "UserService"
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_list_relations():
    """测试列出关系"""
    temp_dir = _setup_test_data()
    try:
        app = create_app(temp_dir)
        client = TestClient(app)
        
        response = client.get("/api/relations")
        assert response.status_code == 200
        data = response.json()
        assert "relations" in data
        assert data["total"] == 2
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_get_graph_data():
    """测试获取图谱数据"""
    temp_dir = _setup_test_data()
    try:
        app = create_app(temp_dir)
        client = TestClient(app)
        
        response = client.get("/api/graph/data")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_get_stats():
    """测试获取统计信息"""
    temp_dir = _setup_test_data()
    try:
        app = create_app(temp_dir)
        client = TestClient(app)
        
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["entities"] == 3
        assert data["relations"] == 2
        assert "entity_types" in data
        assert "relation_types" in data
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_web_ui():
    """测试Web UI页面"""
    temp_dir = _setup_test_data()
    try:
        app = create_app(temp_dir)
        client = TestClient(app)
        
        response = client.get("/")
        assert response.status_code == 200
        assert "RepoMind" in response.text
        assert "vis-network" in response.text
    finally:
        import shutil
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_list_projects()
    test_get_project()
    test_search()
    test_get_entity()
    test_get_entity_not_found()
    test_list_entities()
    test_list_entities_by_type()
    test_list_relations()
    test_get_graph_data()
    test_get_stats()
    test_web_ui()
    print("所有 web_ui 测试通过!")
