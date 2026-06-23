"""集成测试 - 端到端测试完整工作流"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from repomind.models import KnowledgeGraph, Entity, Relation, EntityType, RelationType
from repomind.knowledge_extractor import KnowledgeExtractor
from repomind.graph_builder import GraphBuilder
from repomind.query_engine import QueryEngine
from repomind.qa_engine import QAEngine
from repomind.flow_analyzer import FlowAnalyzer, analyze_project_flows
from repomind.graph_diff import diff_graphs
from repomind.graph_merge import merge_graphs, MergeOptions
from repomind.advanced_search import search_entities, SearchOptions
from repomind.incremental import IncrementalAnalyzer


def _create_test_project(base_dir: str):
    """创建测试项目"""
    project_dir = Path(base_dir) / "test-project"
    project_dir.mkdir(exist_ok=True)
    
    # 创建 README.md
    readme = project_dir / "README.md"
    readme.write_text("""# Test Project

这是一个测试项目。

## 技术栈

- Python 3.11
- FastAPI
- PostgreSQL
- Redis

## 模块

### UserService
用户服务模块，处理用户相关操作。

### OrderService
订单服务模块，处理订单相关操作。
""")
    
    # 创建代码文件
    src_dir = project_dir / "src"
    src_dir.mkdir(exist_ok=True)
    
    user_service = src_dir / "user_service.py"
    user_service.write_text("""from fastapi import FastAPI

app = FastAPI()

class UserService:
    def get_user(self):
        return self._fetch_from_db()
    
    def _fetch_from_db(self):
        return {}

@app.get("/users")
def list_users():
    return []
""")
    
    order_service = src_dir / "order_service.py"
    order_service.write_text("""class OrderService:
    def create_order(self, user_id):
        return self._process_order(user_id)
    
    def _process_order(self, user_id):
        return {}
""")
    
    return project_dir


def test_full_workflow():
    """测试完整工作流: 分析 → 查询 → 搜索"""
    temp_dir = tempfile.mkdtemp()
    try:
        # 1. 创建测试项目
        project_dir = _create_test_project(temp_dir)
        
        # 2. 分析项目
        extractor = KnowledgeExtractor()
        builder = GraphBuilder(temp_dir)
        
        # 读取文件
        md_files = list(project_dir.glob("**/*.md"))
        code_files = list(project_dir.glob("**/*.py"))
        
        from repomind.models import Document
        
        documents = []
        for f in md_files:
            content = f.read_text()
            headings = [line.replace('#', '').strip() for line in content.split('\n') if line.startswith('#')]
            documents.append(Document(
                path=str(f.relative_to(project_dir)),
                content=content,
                title=f.stem,
                headings=headings
            ))
        
        code_contents = []
        for f in code_files:
            code_contents.append((str(f.relative_to(project_dir)), f.read_text()))
        
        # 提取知识
        entities, relations = extractor.extract_from_documents(documents, code_contents)
        
        assert len(entities) > 0, "应该提取到实体"
        assert len(relations) > 0, "应该提取到关系"
        
        # 3. 构建图谱
        graph = builder.build_graph(entities, relations, "test-project")
        
        assert len(graph.entities) > 0
        assert len(graph.relations) > 0
        
        # 4. 查询
        qe = QueryEngine(graph)
        
        modules = qe.find_entities_by_type(EntityType.MODULE)
        assert len(modules) > 0, "应该找到模块"
        
        # 5. 问答
        qa = QAEngine(graph)
        answer = qa.answer_question("有哪些模块？")
        assert "模块" in answer or "Service" in answer
        
        # 6. 搜索
        results = search_entities(graph, SearchOptions(query="Service"))
        assert len(results) > 0, "应该搜索到结果"
        
    finally:
        shutil.rmtree(temp_dir)


def test_analyze_and_export():
    """测试分析和导出"""
    temp_dir = tempfile.mkdtemp()
    try:
        project_dir = _create_test_project(temp_dir)
        
        # 分析
        extractor = KnowledgeExtractor()
        builder = GraphBuilder(temp_dir)
        
        md_files = list(project_dir.glob("**/*.md"))
        code_files = list(project_dir.glob("**/*.py"))
        
        from repomind.models import Document
        
        documents = []
        for f in md_files:
            content = f.read_text()
            headings = [line.replace('#', '').strip() for line in content.split('\n') if line.startswith('#')]
            documents.append(Document(
                path=str(f.relative_to(project_dir)),
                content=content,
                title=f.stem,
                headings=headings
            ))
        
        code_contents = []
        for f in code_files:
            code_contents.append((str(f.relative_to(project_dir)), f.read_text()))
        
        entities, relations = extractor.extract_from_documents(documents, code_contents)
        graph = builder.build_graph(entities, relations, "test-project")
        
        # 导出JSON
        json_path = Path(temp_dir) / "export.json"
        import json
        with open(json_path, 'w') as f:
            json.dump(graph.model_dump(), f, ensure_ascii=False, indent=2)
        
        assert json_path.exists()
        
        # 验证导出内容
        with open(json_path) as f:
            data = json.load(f)
        
        assert "entities" in data
        assert "relations" in data
        assert len(data["entities"]) > 0
        
    finally:
        shutil.rmtree(temp_dir)


def test_diff_and_merge_workflow():
    """测试对比和合并工作流"""
    # 创建两个图谱
    graph1 = KnowledgeGraph(
        entities=[
            Entity(name="ServiceA", type=EntityType.MODULE, description="服务A"),
            Entity(name="Database", type=EntityType.DATABASE, description="PostgreSQL"),
        ],
        relations=[
            Relation(source="ServiceA", target="Database", type=RelationType.DEPENDS_ON),
        ]
    )
    
    graph2 = KnowledgeGraph(
        entities=[
            Entity(name="ServiceA", type=EntityType.MODULE, description="服务A v2"),
            Entity(name="ServiceB", type=EntityType.MODULE, description="服务B"),
            Entity(name="Database", type=EntityType.DATABASE, description="PostgreSQL"),
        ],
        relations=[
            Relation(source="ServiceA", target="Database", type=RelationType.DEPENDS_ON),
            Relation(source="ServiceB", target="Database", type=RelationType.DEPENDS_ON),
        ]
    )
    
    # 1. 对比
    diff = diff_graphs(graph1, graph2)
    
    assert diff.entities_added == 1  # ServiceB
    assert diff.entities_modified == 1  # ServiceA description changed
    assert diff.relations_added == 1  # ServiceB -> Database
    
    # 2. 合并
    result = merge_graphs([
        ("project1", graph1),
        ("project2", graph2)
    ], MergeOptions(conflict_strategy='overwrite'))
    
    assert len(result.merged_graph.entities) == 3  # ServiceA, Database, ServiceB
    assert len(result.merged_graph.relations) == 2


def test_flow_analysis_workflow():
    """测试流程分析工作流"""
    code_files = [
        ("app.py", '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/users")
def list_users():
    """List all users"""
    return fetch_users()

def fetch_users():
    """Fetch users from db"""
    return []
'''),
    ]
    
    analyzer = analyze_project_flows(code_files)
    
    assert len(analyzer.api_endpoints) >= 1
    assert analyzer.api_endpoints[0].method == "GET"
    assert analyzer.api_endpoints[0].path == "/users"


def test_incremental_workflow():
    """测试增量更新工作流"""
    temp_dir = tempfile.mkdtemp()
    try:
        project_dir = Path(temp_dir) / "project"
        project_dir.mkdir()
        
        # 创建初始文件
        file1 = project_dir / "file1.py"
        file1.write_text("class ServiceA: pass")
        
        # 初始化增量分析器
        extractor = KnowledgeExtractor()
        manifest_path = Path(temp_dir) / "manifest.json"
        incremental = IncrementalAnalyzer(extractor, manifest_path)
        
        # 首次分析
        manifest = incremental.load_manifest()
        assert len(manifest.files) == 0
        
        # 模拟文件哈希
        from repomind.incremental import compute_hash
        current = {}
        for f in project_dir.glob("**/*.py"):
            content = f.read_text()
            current[str(f)] = compute_hash(content)
        
        # 检测变化 (注意参数顺序: current, manifest)
        added, modified, deleted = incremental.detect_changes(current, manifest)
        assert len(added) == 1  # file1.py 是新增的
        
        # 添加新文件
        file2 = project_dir / "file2.py"
        file2.write_text("class ServiceB: pass")
        
        # 更新哈希
        content2 = file2.read_text()
        current[str(file2)] = compute_hash(content2)
        
        # 再次检测
        added, modified, deleted = incremental.detect_changes(current, manifest)
        assert len(added) == 2  # file1.py 和 file2.py
        
    finally:
        shutil.rmtree(temp_dir)


def test_search_workflow():
    """测试搜索工作流"""
    graph = KnowledgeGraph(
        entities=[
            Entity(name="UserService", type=EntityType.MODULE, description="用户服务"),
            Entity(name="OrderService", type=EntityType.MODULE, description="订单服务"),
            Entity(name="Database", type=EntityType.DATABASE, description="PostgreSQL"),
            Entity(name="Redis", type=EntityType.TOOL, description="缓存"),
        ],
        relations=[
            Relation(source="UserService", target="Database", type=RelationType.DEPENDS_ON),
            Relation(source="OrderService", target="Database", type=RelationType.DEPENDS_ON),
        ]
    )
    
    # 1. 精确搜索
    results = search_entities(graph, SearchOptions(query="UserService"))
    assert len(results) == 1
    assert results[0].entity.name == "UserService"
    
    # 2. 包含搜索
    results = search_entities(graph, SearchOptions(query="Service"))
    assert len(results) == 2
    
    # 3. 类型过滤
    results = search_entities(graph, SearchOptions(query="Service", entity_types=["Module"]))
    assert len(results) == 2
    
    results = search_entities(graph, SearchOptions(query="Service", entity_types=["Database"]))
    assert len(results) == 0
    
    # 4. 正则搜索
    results = search_entities(graph, SearchOptions(query="^User.*", use_regex=True))
    assert len(results) == 1
    
    # 5. 模糊搜索
    results = search_entities(graph, SearchOptions(query="UsrService", fuzzy=True, fuzzy_threshold=0.6))
    assert len(results) >= 1


def test_multi_project_workflow():
    """测试多项目工作流"""
    # 创建多个图谱
    graphs = []
    for i in range(3):
        graph = KnowledgeGraph(
            entities=[
                Entity(name=f"Service{i}", type=EntityType.MODULE, description=f"服务{i}"),
                Entity(name="Database", type=EntityType.DATABASE, description="PostgreSQL"),
            ],
            relations=[
                Relation(source=f"Service{i}", target="Database", type=RelationType.DEPENDS_ON),
            ]
        )
        graphs.append((f"project{i}", graph))
    
    # 合并所有图谱
    result = merge_graphs(graphs, MergeOptions(prefix_project=True))
    
    # 验证
    assert len(result.merged_graph.entities) == 6  # 3个Service + 3个Database(带前缀)
    assert len(result.merged_graph.relations) == 3
    assert len(result.source_projects) == 3


def test_web_api_workflow():
    """测试Web API工作流"""
    from fastapi.testclient import TestClient
    from repomind.web_ui import create_app
    
    temp_dir = tempfile.mkdtemp()
    try:
        # 创建测试数据
        graph = KnowledgeGraph(
            entities=[
                Entity(name="TestModule", type=EntityType.MODULE, description="测试模块"),
            ],
            relations=[]
        )
        
        builder = GraphBuilder(temp_dir)
        builder.save_graph(graph, "test")
        
        # 创建应用
        app = create_app(temp_dir)
        client = TestClient(app)
        
        # 1. 列出项目
        response = client.get("/api/projects")
        assert response.status_code == 200
        assert len(response.json()["projects"]) > 0
        
        # 2. 搜索
        response = client.post("/api/search", json={"query": "Test"})
        assert response.status_code == 200
        assert len(response.json()["results"]) > 0
        
        # 3. 获取统计
        response = client.get("/api/stats?project=test")
        assert response.status_code == 200
        assert response.json()["entities"] == 1
        
        # 4. 获取图谱数据
        response = client.get("/api/graph/data?project=test")
        assert response.status_code == 200
        assert len(response.json()["nodes"]) == 1
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_full_workflow()
    test_analyze_and_export()
    test_diff_and_merge_workflow()
    test_flow_analysis_workflow()
    test_incremental_workflow()
    test_search_workflow()
    test_multi_project_workflow()
    test_web_api_workflow()
    print("所有集成测试通过!")
