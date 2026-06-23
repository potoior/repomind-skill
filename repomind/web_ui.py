"""Web UI - 基于FastAPI的在线查询和图谱可视化"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import json
from pathlib import Path

from .models import KnowledgeGraph, Entity, Relation, EntityType, RelationType
from .graph_builder import GraphBuilder
from .query_engine import QueryEngine
from .qa_engine import QAEngine
from .advanced_search import search_entities, SearchOptions, search_with_context
from .graph_diff import diff_graphs
from .graph_merge import merge_graphs, MergeOptions


app = FastAPI(
    title="RepoMind Web UI",
    description="智能项目知识图谱 - 在线查询和可视化",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局状态
_state = {
    "output_dir": Path("output"),
    "graphs": {},  # name -> KnowledgeGraph
    "current_graph": None,
    "current_name": None,
}


def set_output_dir(output_dir: str):
    """设置输出目录"""
    _state["output_dir"] = Path(output_dir)
    _load_all_graphs()


def _load_all_graphs():
    """加载所有图谱"""
    output_dir = _state["output_dir"]
    if not output_dir.exists():
        return
    
    for graph_file in output_dir.glob("*.graph.json"):
        name = graph_file.stem.replace(".graph", "")
        try:
            graph = GraphBuilder(str(output_dir)).load_graph(name)
            _state["graphs"][name] = graph
        except Exception:
            pass


def _get_graph(name: str = None) -> KnowledgeGraph:
    """获取图谱"""
    if name:
        if name not in _state["graphs"]:
            raise HTTPException(status_code=404, detail=f"项目不存在: {name}")
        return _state["graphs"][name]
    
    if _state["current_graph"]:
        return _state["current_graph"]
    
    if _state["graphs"]:
        return list(_state["graphs"].values())[0]
    
    raise HTTPException(status_code=404, detail="没有可用的知识图谱")


# ============ API 端点 ============

class QueryRequest(BaseModel):
    question: str
    project: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    entity_types: Optional[List[str]] = None
    use_regex: bool = False
    fuzzy: bool = False
    fuzzy_threshold: float = 0.6
    max_results: int = 50


class MergeRequest(BaseModel):
    projects: List[str]
    output_name: str
    strategy: str = "skip"


@app.get("/api/projects", tags=["项目"])
async def list_projects():
    """列出所有项目"""
    projects = []
    for name, graph in _state["graphs"].items():
        projects.append({
            "name": name,
            "entities": len(graph.entities),
            "relations": len(graph.relations),
        })
    return {"projects": projects}


@app.get("/api/projects/{name}", tags=["项目"])
async def get_project(name: str):
    """获取项目详情"""
    graph = _get_graph(name)
    
    # 统计各类型实体
    type_counts = {}
    for e in graph.entities:
        type_counts[e.type.value] = type_counts.get(e.type.value, 0) + 1
    
    return {
        "name": name,
        "entities": len(graph.entities),
        "relations": len(graph.relations),
        "types": type_counts,
    }


@app.post("/api/query", tags=["查询"])
async def query_graph(request: QueryRequest):
    """自然语言查询"""
    graph = _get_graph(request.project)
    qa = QAEngine(graph)
    answer = qa.answer_question(request.question)
    return {"answer": answer}


@app.post("/api/search", tags=["查询"])
async def search_graph(request: SearchRequest):
    """搜索实体"""
    graph = _get_graph()
    
    options = SearchOptions(
        query=request.query,
        entity_types=request.entity_types,
        use_regex=request.use_regex,
        fuzzy=request.fuzzy,
        fuzzy_threshold=request.fuzzy_threshold,
        max_results=request.max_results,
    )
    
    results = search_entities(graph, options)
    
    return {
        "results": [
            {
                "name": r.entity.name,
                "type": r.entity.type.value,
                "description": r.entity.description,
                "source_file": r.entity.source_file,
                "score": r.score,
                "match_type": r.match_type,
            }
            for r in results
        ]
    }


@app.get("/api/entity/{name}", tags=["实体"])
async def get_entity(name: str, project: str = None):
    """获取实体详情和关联"""
    graph = _get_graph(project)
    result = search_with_context(graph, name)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"实体不存在: {name}")
    
    return result


@app.get("/api/entities", tags=["实体"])
async def list_entities(
    type: str = None,
    project: str = None,
    limit: int = 100
):
    """列出实体"""
    graph = _get_graph(project)
    
    entities = graph.entities
    if type:
        entities = [e for e in entities if e.type.value == type]
    
    return {
        "entities": [
            {
                "name": e.name,
                "type": e.type.value,
                "description": e.description,
                "source_file": e.source_file,
            }
            for e in entities[:limit]
        ],
        "total": len(entities),
    }


@app.get("/api/relations", tags=["关系"])
async def list_relations(project: str = None, limit: int = 100):
    """列出关系"""
    graph = _get_graph(project)
    
    return {
        "relations": [
            {
                "source": r.source,
                "target": r.target,
                "type": r.type.value,
                "description": r.description,
            }
            for r in graph.relations[:limit]
        ],
        "total": len(graph.relations),
    }


@app.get("/api/graph/data", tags=["图谱"])
async def get_graph_data(project: str = None):
    """获取图谱可视化数据（vis.js格式）"""
    graph = _get_graph(project)
    
    nodes = []
    for i, entity in enumerate(graph.entities):
        nodes.append({
            "id": i,
            "label": entity.name,
            "group": entity.type.value,
            "title": f"{entity.type.value}: {entity.name}",
        })
    
    # 建立实体索引
    entity_map = {}
    for i, entity in enumerate(graph.entities):
        entity_map[entity.name.lower()] = i
    
    edges = []
    for r in graph.relations:
        source_id = entity_map.get(r.source.lower())
        target_id = entity_map.get(r.target.lower())
        if source_id is not None and target_id is not None:
            edges.append({
                "from": source_id,
                "to": target_id,
                "label": r.type.value,
                "arrows": "to",
            })
    
    return {"nodes": nodes, "edges": edges}


@app.get("/api/stats", tags=["统计"])
async def get_stats(project: str = None):
    """获取统计信息"""
    graph = _get_graph(project)
    
    type_counts = {}
    for e in graph.entities:
        type_counts[e.type.value] = type_counts.get(e.type.value, 0) + 1
    
    relation_counts = {}
    for r in graph.relations:
        relation_counts[r.type.value] = relation_counts.get(r.type.value, 0) + 1
    
    return {
        "entities": len(graph.entities),
        "relations": len(graph.relations),
        "entity_types": type_counts,
        "relation_types": relation_counts,
    }


@app.post("/api/diff", tags=["图谱操作"])
async def diff_projects(project1: str, project2: str):
    """比较两个项目"""
    graph1 = _get_graph(project1)
    graph2 = _get_graph(project2)
    
    diff = diff_graphs(graph1, graph2)
    
    return {
        "entities_added": diff.entities_added,
        "entities_deleted": diff.entities_deleted,
        "entities_modified": diff.entities_modified,
        "relations_added": diff.relations_added,
        "relations_deleted": diff.relations_deleted,
        "entity_changes": [c.model_dump() for c in diff.entity_changes],
        "relation_changes": [c.model_dump() for c in diff.relation_changes],
    }


@app.post("/api/merge", tags=["图谱操作"])
async def merge_projects(request: MergeRequest):
    """合并多个项目"""
    graphs = []
    for name in request.projects:
        graph = _get_graph(name)
        graphs.append((name, graph))
    
    options = MergeOptions(conflict_strategy=request.strategy)
    result = merge_graphs(graphs, options)
    
    # 保存合并结果
    builder = GraphBuilder(str(_state["output_dir"]))
    builder.save_graph(result.merged_graph, request.output_name)
    
    # 更新缓存
    _state["graphs"][request.output_name] = result.merged_graph
    
    return {
        "name": request.output_name,
        "entities": len(result.merged_graph.entities),
        "relations": len(result.merged_graph.relations),
        "conflicts": len(result.conflicts),
    }


# ============ CRUD 操作 ============

class EntityCreate(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    source_file: Optional[str] = None


class EntityUpdate(BaseModel):
    type: Optional[str] = None
    description: Optional[str] = None
    source_file: Optional[str] = None


class RelationCreate(BaseModel):
    source: str
    target: str
    type: str
    description: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str


def _save_graph(name: str, graph: KnowledgeGraph):
    """保存图谱到文件"""
    builder = GraphBuilder(str(_state["output_dir"]))
    builder.save_graph(graph, name)
    _state["graphs"][name] = graph


def _validate_entity_type(type_str: str) -> EntityType:
    """验证实体类型"""
    try:
        return EntityType(type_str)
    except ValueError:
        valid_types = [t.value for t in EntityType]
        raise HTTPException(
            status_code=400,
            detail=f"无效的实体类型: {type_str}。有效类型: {valid_types}"
        )


def _validate_relation_type(type_str: str) -> RelationType:
    """验证关系类型"""
    try:
        return RelationType(type_str)
    except ValueError:
        valid_types = [t.value for t in RelationType]
        raise HTTPException(
            status_code=400,
            detail=f"无效的关系类型: {type_str}。有效类型: {valid_types}"
        )


@app.post("/api/projects", tags=["项目CRUD"])
async def create_project(request: ProjectCreate):
    """创建新项目"""
    if request.name in _state["graphs"]:
        raise HTTPException(status_code=409, detail=f"项目已存在: {request.name}")
    
    graph = KnowledgeGraph(entities=[], relations=[])
    _save_graph(request.name, graph)
    
    return {
        "name": request.name,
        "entities": 0,
        "relations": 0,
        "message": "项目创建成功"
    }


@app.put("/api/projects/{name}", tags=["项目CRUD"])
async def update_project(name: str, new_name: str = Query(...)):
    """重命名项目"""
    if name not in _state["graphs"]:
        raise HTTPException(status_code=404, detail=f"项目不存在: {name}")
    
    if new_name in _state["graphs"]:
        raise HTTPException(status_code=409, detail=f"目标名称已存在: {new_name}")
    
    graph = _state["graphs"][name]
    
    # 保存为新名称
    _save_graph(new_name, graph)
    
    # 删除旧文件
    old_file = _state["output_dir"] / f"{name}.graph.json"
    old_html = _state["output_dir"] / f"{name}.graph.html"
    if old_file.exists():
        old_file.unlink()
    if old_html.exists():
        old_html.unlink()
    
    # 更新缓存
    del _state["graphs"][name]
    
    return {
        "old_name": name,
        "new_name": new_name,
        "message": "项目重命名成功"
    }


@app.delete("/api/projects/{name}", tags=["项目CRUD"])
async def delete_project(name: str):
    """删除项目"""
    if name not in _state["graphs"]:
        raise HTTPException(status_code=404, detail=f"项目不存在: {name}")
    
    # 删除文件
    graph_file = _state["output_dir"] / f"{name}.graph.json"
    html_file = _state["output_dir"] / f"{name}.graph.html"
    
    if graph_file.exists():
        graph_file.unlink()
    if html_file.exists():
        html_file.unlink()
    
    # 更新缓存
    del _state["graphs"][name]
    
    return {"message": f"项目 {name} 已删除"}


@app.post("/api/entities", tags=["实体CRUD"])
async def create_entity(entity: EntityCreate, project: str = Query(None)):
    """创建实体"""
    graph = _get_graph(project)
    
    # 检查是否已存在
    for e in graph.entities:
        if e.name == entity.name and e.type.value == entity.type:
            raise HTTPException(status_code=409, detail=f"实体已存在: {entity.name}")
    
    # 验证类型
    etype = _validate_entity_type(entity.type)
    
    # 创建实体
    new_entity = Entity(
        name=entity.name,
        type=etype,
        description=entity.description,
        source_file=entity.source_file
    )
    
    graph.entities.append(new_entity)
    
    # 保存
    project_name = project or list(_state["graphs"].keys())[0]
    _save_graph(project_name, graph)
    
    return {
        "name": new_entity.name,
        "type": new_entity.type.value,
        "description": new_entity.description,
        "message": "实体创建成功"
    }


@app.put("/api/entity/{name}", tags=["实体CRUD"])
async def update_entity(name: str, update: EntityUpdate, project: str = Query(None)):
    """更新实体"""
    graph = _get_graph(project)
    
    # 查找实体
    entity = None
    for e in graph.entities:
        if e.name == name:
            entity = e
            break
    
    if not entity:
        raise HTTPException(status_code=404, detail=f"实体不存在: {name}")
    
    # 更新字段
    if update.type is not None:
        entity.type = _validate_entity_type(update.type)
    if update.description is not None:
        entity.description = update.description
    if update.source_file is not None:
        entity.source_file = update.source_file
    
    # 保存
    project_name = project or list(_state["graphs"].keys())[0]
    _save_graph(project_name, graph)
    
    return {
        "name": entity.name,
        "type": entity.type.value,
        "description": entity.description,
        "source_file": entity.source_file,
        "message": "实体更新成功"
    }


@app.delete("/api/entity/{name}", tags=["实体CRUD"])
async def delete_entity(name: str, project: str = Query(None)):
    """删除实体"""
    graph = _get_graph(project)
    
    # 查找并删除实体
    original_count = len(graph.entities)
    graph.entities = [e for e in graph.entities if e.name != name]
    
    if len(graph.entities) == original_count:
        raise HTTPException(status_code=404, detail=f"实体不存在: {name}")
    
    # 同时删除相关关系
    graph.relations = [
        r for r in graph.relations
        if r.source != name and r.target != name
    ]
    
    # 保存
    project_name = project or list(_state["graphs"].keys())[0]
    _save_graph(project_name, graph)
    
    return {"message": f"实体 {name} 及其相关关系已删除"}


@app.post("/api/relations", tags=["关系CRUD"])
async def create_relation(relation: RelationCreate, project: str = Query(None)):
    """创建关系"""
    graph = _get_graph(project)
    
    # 验证类型
    rtype = _validate_relation_type(relation.type)
    
    # 检查源和目标实体是否存在
    source_exists = any(e.name == relation.source for e in graph.entities)
    target_exists = any(e.name == relation.target for e in graph.entities)
    
    if not source_exists:
        raise HTTPException(status_code=404, detail=f"源实体不存在: {relation.source}")
    if not target_exists:
        raise HTTPException(status_code=404, detail=f"目标实体不存在: {relation.target}")
    
    # 检查关系是否已存在
    for r in graph.relations:
        if r.source == relation.source and r.target == relation.target and r.type == rtype:
            raise HTTPException(status_code=409, detail="关系已存在")
    
    # 创建关系
    new_relation = Relation(
        source=relation.source,
        target=relation.target,
        type=rtype,
        description=relation.description
    )
    
    graph.relations.append(new_relation)
    
    # 保存
    project_name = project or list(_state["graphs"].keys())[0]
    _save_graph(project_name, graph)
    
    return {
        "source": new_relation.source,
        "target": new_relation.target,
        "type": new_relation.type.value,
        "message": "关系创建成功"
    }


@app.delete("/api/relations", tags=["关系CRUD"])
async def delete_relation(
    source: str = Query(...),
    target: str = Query(...),
    type: str = Query(...),
    project: str = Query(None)
):
    """删除关系"""
    graph = _get_graph(project)
    
    rtype = _validate_relation_type(type)
    
    # 查找并删除关系
    original_count = len(graph.relations)
    graph.relations = [
        r for r in graph.relations
        if not (r.source == source and r.target == target and r.type == rtype)
    ]
    
    if len(graph.relations) == original_count:
        raise HTTPException(status_code=404, detail="关系不存在")
    
    # 保存
    project_name = project or list(_state["graphs"].keys())[0]
    _save_graph(project_name, graph)
    
    return {"message": "关系已删除"}


@app.get("/api/types", tags=["元数据"])
async def get_valid_types():
    """获取有效的实体和关系类型"""
    return {
        "entity_types": [t.value for t in EntityType],
        "relation_types": [t.value for t in RelationType]
    }


# ============ Web UI 页面 ============

@app.get("/", response_class=HTMLResponse, tags=["Web UI"])
async def web_ui():
    """主页"""
    return _get_web_ui_html()


def _get_web_ui_html() -> str:
    """生成Web UI HTML"""
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RepoMind - 知识图谱</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #eee; }
        
        .container { display: flex; height: 100vh; }
        
        /* 侧边栏 */
        .sidebar {
            width: 300px; background: #16213e; padding: 20px;
            overflow-y: auto; border-right: 1px solid #0f3460;
        }
        .sidebar h1 {
            font-size: 24px; margin-bottom: 20px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        
        /* 搜索框 */
        .search-box {
            width: 100%; padding: 12px; margin-bottom: 20px;
            background: #0f3460; border: 1px solid #1a1a4e;
            border-radius: 8px; color: #eee; font-size: 14px;
        }
        .search-box:focus { outline: none; border-color: #667eea; }
        
        /* 项目列表 */
        .project-list { margin-bottom: 20px; }
        .project-item {
            padding: 10px; margin-bottom: 5px; background: #0f3460;
            border-radius: 6px; cursor: pointer; transition: all 0.2s;
        }
        .project-item:hover { background: #1a1a4e; }
        .project-item.active { background: #667eea; }
        .project-item .name { font-weight: bold; }
        .project-item .stats { font-size: 12px; color: #888; }
        
        /* 统计卡片 */
        .stats-grid {
            display: grid; grid-template-columns: 1fr 1fr;
            gap: 10px; margin-bottom: 20px;
        }
        .stat-card {
            background: #0f3460; padding: 15px; border-radius: 8px;
            text-align: center;
        }
        .stat-card .number { font-size: 24px; font-weight: bold; color: #667eea; }
        .stat-card .label { font-size: 12px; color: #888; }
        
        /* 查询区域 */
        .query-section { margin-top: 20px; }
        .query-input {
            width: 100%; padding: 12px; margin-bottom: 10px;
            background: #0f3460; border: 1px solid #1a1a4e;
            border-radius: 8px; color: #eee; font-size: 14px;
        }
        .query-btn {
            width: 100%; padding: 12px; background: linear-gradient(135deg, #667eea, #764ba2);
            border: none; border-radius: 8px; color: white;
            font-size: 14px; cursor: pointer; transition: all 0.2s;
        }
        .query-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102,126,234,0.4); }
        
        /* 结果区域 */
        .result-box {
            margin-top: 10px; padding: 15px; background: #0f3460;
            border-radius: 8px; max-height: 200px; overflow-y: auto;
            font-size: 13px; line-height: 1.6;
        }
        
        /* 主区域 */
        .main { flex: 1; display: flex; flex-direction: column; }
        
        /* 工具栏 */
        .toolbar {
            padding: 15px; background: #16213e;
            border-bottom: 1px solid #0f3460;
            display: flex; gap: 10px;
        }
        .toolbar-btn {
            padding: 8px 16px; background: #0f3460;
            border: 1px solid #1a1a4e; border-radius: 6px;
            color: #eee; cursor: pointer; transition: all 0.2s;
        }
        .toolbar-btn:hover { background: #1a1a4e; }
        .toolbar-btn.active { background: #667eea; border-color: #667eea; }
        
        /* 图谱区域 */
        .graph-container { flex: 1; position: relative; }
        #network { width: 100%; height: 100%; }
        
        /* 详情面板 */
        .detail-panel {
            position: absolute; top: 20px; right: 20px;
            width: 350px; background: rgba(22, 33, 62, 0.95);
            border-radius: 12px; padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            display: none;
        }
        .detail-panel.visible { display: block; }
        .detail-panel h3 { color: #667eea; margin-bottom: 15px; }
        .detail-row { padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .detail-label { color: #888; font-size: 12px; }
        .detail-value { color: #eee; font-size: 14px; }
        .close-btn {
            position: absolute; top: 10px; right: 10px;
            background: none; border: none; color: #888;
            cursor: pointer; font-size: 18px;
        }
        
        /* 图例 */
        .legend {
            position: absolute; bottom: 20px; left: 20px;
            background: rgba(22, 33, 62, 0.95); border-radius: 8px;
            padding: 15px; font-size: 12px;
        }
        .legend-item { display: flex; align-items: center; margin-bottom: 5px; }
        .legend-color { width: 12px; height: 12px; border-radius: 3px; margin-right: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>📊 RepoMind</h1>
            
            <input type="text" class="search-box" id="searchInput" placeholder="🔍 搜索实体...">
            
            <div class="project-list" id="projectList">
                <h3 style="margin-bottom: 10px; color: #888;">📁 项目列表</h3>
            </div>
            
            <div class="stats-grid" id="statsGrid">
                <div class="stat-card">
                    <div class="number" id="entityCount">-</div>
                    <div class="label">实体</div>
                </div>
                <div class="stat-card">
                    <div class="number" id="relationCount">-</div>
                    <div class="label">关系</div>
                </div>
            </div>
            
            <div class="query-section">
                <h3 style="margin-bottom: 10px; color: #888;">💬 智能问答</h3>
                <input type="text" class="query-input" id="queryInput" placeholder="输入问题...">
                <button class="query-btn" onclick="executeQuery()">提问</button>
                <div class="result-box" id="queryResult" style="display: none;"></div>
            </div>
        </div>
        
        <div class="main">
            <div class="toolbar">
                <button class="toolbar-btn" onclick="resetView()">重置视图</button>
                <button class="toolbar-btn" onclick="togglePhysics()">物理引擎</button>
                <button class="toolbar-btn" onclick="exportImage()">导出图片</button>
            </div>
            
            <div class="graph-container">
                <div id="network"></div>
                
                <div class="detail-panel" id="detailPanel">
                    <button class="close-btn" onclick="closeDetail()">×</button>
                    <h3 id="detailTitle">实体详情</h3>
                    <div id="detailContent"></div>
                </div>
                
                <div class="legend" id="legend"></div>
            </div>
        </div>
    </div>
    
    <script>
        let network = null;
        let currentProject = null;
        let physicsEnabled = true;
        
        const typeColors = {
            'Project': '#ff6b6b', 'Module': '#4ecdc4', 'Document': '#45b7d1',
            'Framework': '#96ceb4', 'Database': '#feca57', 'API': '#ff9ff3',
            'Protocol': '#54a0ff', 'Service': '#5f27cd', 'Skill': '#01a3a4',
            'Configuration': '#f368e0', 'Command': '#ff9f43', 'Feature': '#ee5a24',
            'Tool': '#a29bfe'
        };
        
        // 初始化
        async function init() {
            await loadProjects();
            setupSearch();
            setupQuery();
        }
        
        // 加载项目列表
        async function loadProjects() {
            const res = await fetch('/api/projects');
            const data = await res.json();
            
            const list = document.getElementById('projectList');
            list.innerHTML = '<h3 style="margin-bottom: 10px; color: #888;">📁 项目列表</h3>';
            
            data.projects.forEach(p => {
                const item = document.createElement('div');
                item.className = 'project-item';
                item.innerHTML = `
                    <div class="name">${p.name}</div>
                    <div class="stats">${p.entities} 实体 · ${p.relations} 关系</div>
                `;
                item.onclick = () => loadProject(p.name);
                list.appendChild(item);
            });
            
            // 自动加载第一个项目
            if (data.projects.length > 0) {
                loadProject(data.projects[0].name);
            }
        }
        
        // 加载项目
        async function loadProject(name) {
            currentProject = name;
            
            // 更新选中状态
            document.querySelectorAll('.project-item').forEach(el => {
                el.classList.toggle('active', el.querySelector('.name').textContent === name);
            });
            
            // 加载统计
            const statsRes = await fetch(`/api/stats?project=${name}`);
            const stats = await statsRes.json();
            
            document.getElementById('entityCount').textContent = stats.entities;
            document.getElementById('relationCount').textContent = stats.relations;
            
            // 加载图谱
            const graphRes = await fetch(`/api/graph/data?project=${name}`);
            const graphData = await graphRes.json();
            
            renderGraph(graphData);
            renderLegend(stats.entity_types);
        }
        
        // 渲染图谱
        function renderGraph(data) {
            const container = document.getElementById('network');
            
            const nodes = new vis.DataSet(data.nodes.map(n => ({
                ...n,
                font: { color: '#fff', size: 14 },
                borderWidth: 2,
                shadow: true
            })));
            
            const edges = new vis.DataSet(data.edges.map(e => ({
                ...e,
                color: { color: '#666', highlight: '#667eea' },
                font: { color: '#888', size: 10 },
                smooth: { type: 'continuous' }
            })));
            
            const options = {
                groups: Object.fromEntries(
                    Object.entries(typeColors).map(([k, v]) => [k, { color: { background: v, border: v } }])
                ),
                physics: {
                    enabled: true,
                    solver: 'forceAtlas2Based',
                    forceAtlas2Based: {
                        gravitationalConstant: -50,
                        centralGravity: 0.01,
                        springLength: 150,
                        springConstant: 0.08,
                        damping: 0.4
                    },
                    stabilization: { iterations: 150 }
                },
                interaction: { hover: true, tooltipDelay: 200 }
            };
            
            network = new vis.Network(container, { nodes, edges }, options);
            
            // 点击事件
            network.on('click', async (params) => {
                if (params.nodes.length > 0) {
                    const nodeId = params.nodes[0];
                    const node = data.nodes[nodeId];
                    await showDetail(node.label);
                } else {
                    closeDetail();
                }
            });
        }
        
        // 渲染图例
        function renderLegend(types) {
            const legend = document.getElementById('legend');
            legend.innerHTML = Object.entries(types)
                .map(([type, count]) => `
                    <div class="legend-item">
                        <div class="legend-color" style="background: ${typeColors[type] || '#888'}"></div>
                        <span>${type} (${count})</span>
                    </div>
                `).join('');
        }
        
        // 显示详情
        async function showDetail(name) {
            const res = await fetch(`/api/entity/${name}?project=${currentProject}`);
            const data = await res.json();
            
            const panel = document.getElementById('detailPanel');
            const title = document.getElementById('detailTitle');
            const content = document.getElementById('detailContent');
            
            title.textContent = data.entity.name;
            
            let html = `
                <div class="detail-row">
                    <div class="detail-label">类型</div>
                    <div class="detail-value">${data.entity.type}</div>
                </div>
            `;
            
            if (data.entity.description) {
                html += `
                    <div class="detail-row">
                        <div class="detail-label">描述</div>
                        <div class="detail-value">${data.entity.description}</div>
                    </div>
                `;
            }
            
            if (data.outgoing.length > 0) {
                html += `<div class="detail-row"><div class="detail-label">出向关系 (${data.outgoing.length})</div>`;
                data.outgoing.slice(0, 5).forEach(r => {
                    html += `<div class="detail-value">→ ${r.entity} (${r.relation})</div>`;
                });
                html += '</div>';
            }
            
            if (data.incoming.length > 0) {
                html += `<div class="detail-row"><div class="detail-label">入向关系 (${data.incoming.length})</div>`;
                data.incoming.slice(0, 5).forEach(r => {
                    html += `<div class="detail-value">← ${r.entity} (${r.relation})</div>`;
                });
                html += '</div>';
            }
            
            content.innerHTML = html;
            panel.classList.add('visible');
        }
        
        // 关闭详情
        function closeDetail() {
            document.getElementById('detailPanel').classList.remove('visible');
        }
        
        // 搜索
        function setupSearch() {
            const input = document.getElementById('searchInput');
            let timeout;
            
            input.addEventListener('input', () => {
                clearTimeout(timeout);
                timeout = setTimeout(async () => {
                    const query = input.value.trim();
                    if (!query) {
                        loadProject(currentProject);
                        return;
                    }
                    
                    const res = await fetch('/api/search', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ query })
                    });
                    const data = await res.json();
                    
                    // 高亮搜索结果
                    if (network && data.results.length > 0) {
                        const nodeIds = data.results.map(r => {
                            const nodes = network.body.data.nodes.get();
                            const node = nodes.find(n => n.label === r.name);
                            return node ? node.id : null;
                        }).filter(id => id !== null);
                        
                        network.selectNodes(nodeIds);
                        network.focus(nodeIds[0], { scale: 1.5, animation: true });
                    }
                }, 300);
            });
        }
        
        // 查询
        function setupQuery() {
            document.getElementById('queryInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') executeQuery();
            });
        }
        
        async function executeQuery() {
            const input = document.getElementById('queryInput');
            const result = document.getElementById('queryResult');
            const question = input.value.trim();
            
            if (!question) return;
            
            result.style.display = 'block';
            result.innerHTML = '思考中...';
            
            const res = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question, project: currentProject })
            });
            const data = await res.json();
            
            result.innerHTML = data.answer;
        }
        
        // 工具栏
        function resetView() {
            if (network) network.fit({ animation: true });
            closeDetail();
        }
        
        function togglePhysics() {
            physicsEnabled = !physicsEnabled;
            if (network) network.setOptions({ physics: { enabled: physicsEnabled } });
        }
        
        function exportImage() {
            if (!network) return;
            const canvas = document.querySelector('#network canvas');
            const link = document.createElement('a');
            link.download = `${currentProject}_graph.png`;
            link.href = canvas.toDataURL();
            link.click();
        }
        
        // 初始化
        init();
    </script>
</body>
</html>"""


def create_app(output_dir: str = "output") -> FastAPI:
    """创建FastAPI应用"""
    set_output_dir(output_dir)
    return app
