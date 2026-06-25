"""API数据流分析器 - 分析前后端接口和数据流向"""

import re
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class APIEndpoint:
    """API端点"""
    method: str  # GET, POST, PUT, DELETE
    path: str
    handler: str
    file_path: str
    description: str = ""
    request_body: Optional[str] = None
    response_model: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ServiceMethod:
    """服务方法"""
    name: str
    file_path: str
    class_name: str = ""
    calls: List[str] = field(default_factory=list)
    db_operations: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class DataFlow:
    """数据流"""
    endpoint: str
    method: str
    frontend_call: str = ""
    api_handler: str = ""
    service_calls: List[str] = field(default_factory=list)
    db_operations: List[str] = field(default_factory=list)
    response_path: str = ""


class APIDataFlowAnalyzer:
    """API数据流分析器"""
    
    def __init__(self):
        self.endpoints: List[APIEndpoint] = []
        self.services: Dict[str, ServiceMethod] = {}
        self.data_flows: List[DataFlow] = []
        self.models: Dict[str, Dict] = {}
    
    def analyze_backend(self, backend_path: str) -> None:
        """分析后端代码"""
        backend_dir = Path(backend_path)
        
        # 分析API路由
        api_dir = backend_dir / "app" / "api"
        if api_dir.exists():
            for py_file in api_dir.glob("*.py"):
                self._extract_routes(py_file)
        
        # 分析服务层
        services_dir = backend_dir / "app" / "services"
        if services_dir.exists():
            for py_file in services_dir.glob("*.py"):
                self._extract_services(py_file)
        
        # 分析数据模型
        models_dir = backend_dir / "app" / "models"
        if models_dir.exists():
            for py_file in models_dir.glob("*.py"):
                self._extract_models(py_file)
        
        # 分析Schemas
        schemas_dir = backend_dir / "app" / "schemas"
        if schemas_dir.exists():
            for py_file in schemas_dir.glob("*.py"):
                self._extract_schemas(py_file)
    
    def analyze_frontend(self, frontend_path: str) -> None:
        """分析前端代码"""
        frontend_dir = Path(frontend_path)
        
        # 分析前端API调用
        for ext in ['*.js', '*.ts', '*.jsx', '*.tsx', '*.vue']:
            for file in frontend_dir.rglob(ext):
                self._extract_frontend_api_calls(file)
    
    def _extract_routes(self, file_path: Path) -> None:
        """提取API路由"""
        content = file_path.read_text(encoding='utf-8')
        
        # FastAPI路由模式
        patterns = [
            # @router.get("/path")
            r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\'].*?\)\s*\n(?:async\s+)?def\s+(\w+)',
            # @app.get("/path")  
            r'@app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\'].*?\)\s*\n(?:async\s+)?def\s+(\w+)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                method = match.group(1).upper()
                path = match.group(2)
                handler = match.group(3)
                
                # 提取描述（docstring）
                desc_match = re.search(
                    rf'async\s+def\s+{handler}.*?"""(.*?)"""',
                    content, re.DOTALL
                )
                description = desc_match.group(1).strip() if desc_match else ""
                
                # 提取请求体参数
                body_match = re.search(
                    rf'async\s+def\s+{handler}\s*\([^)]*(\w+):\s*(\w+)',
                    content
                )
                request_body = body_match.group(2) if body_match else None
                
                # 提取依赖注入
                deps = []
                dep_pattern = r'(\w+)\s*:\s*(\w+)\s*=\s*Depends\('
                for dep_match in re.finditer(dep_pattern, content):
                    deps.append(dep_match.group(2))
                
                endpoint = APIEndpoint(
                    method=method,
                    path=path,
                    handler=handler,
                    file_path=str(file_path),
                    description=description,
                    request_body=request_body,
                    dependencies=deps
                )
                self.endpoints.append(endpoint)
    
    def _extract_services(self, file_path: Path) -> None:
        """提取服务方法"""
        content = file_path.read_text(encoding='utf-8')
        
        # 提取类定义
        class_pattern = r'class\s+(\w+).*?:'
        for class_match in re.finditer(class_pattern, content):
            class_name = class_match.group(1)
            
            # 提取类中的方法
            method_pattern = rf'class\s+{class_name}.*?(?=class\s|\Z)'
            class_content_match = re.search(method_pattern, content, re.DOTALL)
            if class_content_match:
                class_content = class_content_match.group(0)
                
                for method_match in re.finditer(r'(?:async\s+)?def\s+(\w+)\s*\([^)]*\)', class_content):
                    method_name = method_match.group(1)
                    if method_name.startswith('_') and method_name != '__init__':
                        continue
                    
                    # 分析方法调用
                    method_body = self._extract_method_body(class_content, method_name)
                    calls = self._extract_method_calls(method_body)
                    db_ops = self._extract_db_operations(method_body)
                    
                    service = ServiceMethod(
                        name=method_name,
                        file_path=str(file_path),
                        class_name=class_name,
                        calls=calls,
                        db_operations=db_ops
                    )
                    self.services[f"{class_name}.{method_name}"] = service
    
    def _extract_method_body(self, content: str, method_name: str) -> str:
        """提取方法体"""
        pattern = rf'(?:async\s+)?def\s+{method_name}\s*\([^)]*\)(.*?)(?=\n\s*(?:async\s+)?def\s|\n\s*class\s|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else ""
    
    def _extract_method_calls(self, body: str) -> List[str]:
        """提取方法调用"""
        calls = []
        # self.method() 或 await self.method()
        for match in re.finditer(r'(?:await\s+)?(?:self|cls)\.(\w+)\s*\(', body):
            calls.append(match.group(1))
        # 直接函数调用
        for match in re.finditer(r'(?<!\.)(\w+)\s*\(', body):
            func_name = match.group(1)
            if func_name not in ['if', 'for', 'while', 'return', 'print', 'len', 'str', 'int', 'list', 'dict', 'set', 'True', 'False', 'None']:
                calls.append(func_name)
        return calls
    
    def _extract_db_operations(self, body: str) -> List[str]:
        """提取数据库操作"""
        ops = []
        # SQLAlchemy操作
        db_patterns = [
            (r'\.query\(', 'QUERY'),
            (r'\.add\(', 'INSERT'),
            (r'\.delete\(', 'DELETE'),
            (r'\.commit\(', 'COMMIT'),
            (r'\.execute\(', 'EXECUTE'),
            (r'\.filter\(', 'FILTER'),
            (r'\.filter_by\(', 'FILTER_BY'),
            (r'\.first\(', 'SELECT_ONE'),
            (r'\.all\(', 'SELECT_ALL'),
            (r'\.update\(', 'UPDATE'),
        ]
        for pattern, op_name in db_patterns:
            if re.search(pattern, body):
                ops.append(op_name)
        return ops
    
    def _extract_models(self, file_path: Path) -> None:
        """提取数据模型"""
        content = file_path.read_text(encoding='utf-8')
        
        # SQLAlchemy模型
        pattern = r'class\s+(\w+)\s*\([^)]*Base[^)]*\)(.*?)(?=class\s|\Z)'
        for match in re.finditer(pattern, content, re.DOTALL):
            model_name = match.group(1)
            model_body = match.group(2)
            
            # 提取字段
            fields = []
            for field_match in re.finditer(r'(\w+)\s*=\s*Column\(([^)]+)\)', model_body):
                fields.append({
                    'name': field_match.group(1),
                    'definition': field_match.group(2)
                })
            
            self.models[model_name] = {
                'fields': fields,
                'file_path': str(file_path)
            }
    
    def _extract_schemas(self, file_path: Path) -> None:
        """提取Pydantic Schema"""
        content = file_path.read_text(encoding='utf-8')
        
        pattern = r'class\s+(\w+)\s*\([^)]*BaseModel[^)]*\)(.*?)(?=class\s|\Z)'
        for match in re.finditer(pattern, content, re.DOTALL):
            schema_name = match.group(1)
            schema_body = match.group(2)
            
            fields = []
            for field_match in re.finditer(r'(\w+)\s*:\s*(\w+)', schema_body):
                fields.append({
                    'name': field_match.group(1),
                    'type': field_match.group(2)
                })
            
            self.models[schema_name] = {
                'fields': fields,
                'file_path': str(file_path),
                'type': 'schema'
            }
    
    def _extract_frontend_api_calls(self, file_path: Path) -> None:
        """提取前端API调用"""
        try:
            content = file_path.read_text(encoding='utf-8')
        except:
            return
        
        # axios/fetch API调用模式
        patterns = [
            # axios.get/post/put/delete
            r'axios\.(get|post|put|delete)\s*\(\s*[`"\']([^`"\']+)[`"\']',
            # fetch()
            r'fetch\s*\(\s*[`"\']([^`"\']+)[`"\']',
            # api.get/post/put/delete
            r'api\.(get|post|put|delete)\s*\(\s*[`"\']([^`"\']+)[`"\']',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                if match.lastindex == 2:
                    method = match.group(1).upper()
                    path = match.group(2)
                else:
                    method = "GET"
                    path = match.group(1)
                
                # 关联到后端端点
                for endpoint in self.endpoints:
                    if self._paths_match(endpoint.path, path):
                        endpoint.description = f"前端调用: {file_path.name}"
    
    def _paths_match(self, backend_path: str, frontend_path: str) -> bool:
        """匹配前后端路径"""
        # 移除路径参数的差异
        backend_clean = re.sub(r'\{[^}]+\}', ':id', backend_path)
        frontend_clean = re.sub(r'\$\{[^}]+\}', ':id', frontend_path)
        return backend_clean == frontend_clean
    
    def build_data_flows(self) -> None:
        """构建数据流"""
        for endpoint in self.endpoints:
            flow = DataFlow(
                endpoint=endpoint.path,
                method=endpoint.method,
                api_handler=endpoint.handler
            )
            
            # 查找服务层调用
            handler_body = self._find_handler_body(endpoint.handler)
            if handler_body:
                service_calls = self._extract_service_calls_from_handler(handler_body)
                flow.service_calls = service_calls
                
                # 查找数据库操作
                for service_call in service_calls:
                    if service_call in self.services:
                        service = self.services[service_call]
                        flow.db_operations.extend(service.db_operations)
            
            self.data_flows.append(flow)
    
    def _find_handler_body(self, handler_name: str) -> str:
        """查找处理器函数体"""
        for endpoint in self.endpoints:
            if endpoint.handler == handler_name:
                try:
                    content = Path(endpoint.file_path).read_text(encoding='utf-8')
                    pattern = rf'async\s+def\s+{handler_name}\s*\([^)]*\)(.*?)(?=\n@|\ndef\s|\nclass\s|\Z)'
                    match = re.search(pattern, content, re.DOTALL)
                    return match.group(1) if match else ""
                except:
                    pass
        return ""
    
    def _extract_service_calls_from_handler(self, handler_body: str) -> List[str]:
        """从处理器中提取服务调用"""
        calls = []
        # 查找service.xxx()调用
        for match in re.finditer(r'(?:await\s+)?(?:\w+_service|service)\.(\w+)\s*\(', handler_body):
            calls.append(match.group(1))
        return calls
    
    def generate_report(self) -> str:
        """生成分析报告"""
        lines = []
        lines.append("# AI-Agent-OS 接口数据流分析报告\n")
        
        # API端点汇总
        lines.append("## 一、API端点汇总\n")
        lines.append("| 方法 | 路径 | 处理函数 | 描述 |")
        lines.append("|------|------|----------|------|")
        for ep in self.endpoints:
            lines.append(f"| {ep.method} | `{ep.path}` | `{ep.handler}` | {ep.description} |")
        
        # 按模块分组的详细分析
        lines.append("\n## 二、接口详细数据流\n")
        
        # 按文件分组
        endpoints_by_file = defaultdict(list)
        for ep in self.endpoints:
            file_name = Path(ep.file_path).stem
            endpoints_by_file[file_name].append(ep)
        
        for file_name, endpoints in endpoints_by_file.items():
            lines.append(f"\n### {file_name} 模块\n")
            
            for ep in endpoints:
                lines.append(f"\n#### {ep.method} {ep.path}\n")
                lines.append(f"- **处理函数**: `{ep.handler}`")
                if ep.description:
                    lines.append(f"- **描述**: {ep.description}")
                if ep.request_body:
                    lines.append(f"- **请求体**: `{ep.request_body}`")
                if ep.dependencies:
                    lines.append(f"- **依赖**: {', '.join(ep.dependencies)}")
                
                # 数据流
                flow = next((f for f in self.data_flows if f.endpoint == ep.path), None)
                if flow:
                    lines.append(f"\n**数据流向:**")
                    lines.append(f"```")
                    lines.append(f"前端请求 → {ep.method} {ep.path}")
                    lines.append(f"    ↓")
                    lines.append(f"路由处理器: {ep.handler}()")
                    if flow.service_calls:
                        lines.append(f"    ↓")
                        lines.append(f"服务层调用:")
                        for call in flow.service_calls:
                            lines.append(f"      - {call}()")
                    if flow.db_operations:
                        lines.append(f"    ↓")
                        lines.append(f"数据库操作: {', '.join(set(flow.db_operations))}")
                    lines.append(f"    ↓")
                    lines.append(f"返回响应")
                    lines.append(f"```")
        
        # 服务层分析
        lines.append("\n## 三、服务层分析\n")
        services_by_class = defaultdict(list)
        for key, service in self.services.items():
            services_by_class[service.class_name].append(service)
        
        for class_name, services in services_by_class.items():
            lines.append(f"\n### {class_name}\n")
            lines.append(f"- **文件**: `{services[0].file_path}`")
            lines.append(f"- **方法数量**: {len(services)}")
            lines.append(f"\n| 方法 | 调用的方法 | 数据库操作 |")
            lines.append(f"|------|-----------|-----------|")
            for s in services:
                calls = ', '.join(s.calls[:3]) if s.calls else '-'
                db_ops = ', '.join(s.db_operations) if s.db_operations else '-'
                lines.append(f"| `{s.name}` | {calls} | {db_ops} |")
        
        # 数据模型
        lines.append("\n## 四、数据模型\n")
        for model_name, model_info in self.models.items():
            model_type = model_info.get('type', 'database')
            lines.append(f"\n### {model_name} ({model_type})\n")
            lines.append(f"- **文件**: `{model_info['file_path']}`")
            if model_info['fields']:
                lines.append(f"- **字段**:")
                for field in model_info['fields'][:10]:
                    if isinstance(field, dict):
                        lines.append(f"  - `{field['name']}`: {field.get('type', field.get('definition', ''))}")
        
        return "\n".join(lines)
    
    def generate_mermaid_flowchart(self) -> str:
        """生成Mermaid流程图"""
        lines = ["graph LR"]
        lines.append("    classDef frontend fill:#61dafb,stroke:#21a0c4,color:black")
        lines.append("    classDef api fill:#4CAF50,stroke:#388E3C,color:white")
        lines.append("    classDef service fill:#2196F3,stroke:#1565C0,color:white")
        lines.append("    classDef database fill:#FF9800,stroke:#F57C00,color:white")
        lines.append("")
        
        # 前端节点
        lines.append("    Frontend[\"🌐 前端\"]:::frontend")
        
        # API层
        for i, ep in enumerate(self.endpoints[:10]):  # 限制显示数量
            node_id = f"API_{i}"
            lines.append(f'    {node_id}["{ep.method} {ep.path}"]:::api')
            lines.append(f"    Frontend --> {node_id}")
        
        # 服务层
        service_nodes = {}
        for i, (key, service) in enumerate(list(self.services.items())[:10]):
            node_id = f"SVC_{i}"
            service_nodes[key] = node_id
            lines.append(f'    {node_id}["{service.class_name}.{service.name}"]:::service')
        
        # 连接API到服务
        for i, ep in enumerate(self.endpoints[:10]):
            api_node = f"API_{i}"
            flow = next((f for f in self.data_flows if f.endpoint == ep.path), None)
            if flow and flow.service_calls:
                for call in flow.service_calls[:2]:
                    for key, svc_node in service_nodes.items():
                        if call in key:
                            lines.append(f"    {api_node} --> {svc_node}")
        
        # 数据库节点
        lines.append('    DB[("🗄️ 数据库")]:::database')
        for svc_node in service_nodes.values():
            lines.append(f"    {svc_node} --> DB")
        
        return "\n".join(lines)
    
    def generate_interactive_html(self, project_name: str = "API Data Flow") -> str:
        """生成交互式HTML数据流图"""
        
        # 准备节点和边数据
        nodes = []
        edges = []
        node_id = 0
        
        # 前端节点
        frontend_id = node_id
        nodes.append({
            "id": node_id,
            "label": "🌐 前端",
            "group": "frontend",
            "level": 0
        })
        node_id += 1
        
        # API层节点
        api_nodes = {}
        for ep in self.endpoints:
            api_id = node_id
            api_nodes[ep.path] = api_id
            nodes.append({
                "id": node_id,
                "label": f"{ep.method}\n{ep.path}",
                "group": "api",
                "level": 1,
                "title": f"{ep.method} {ep.path}\nHandler: {ep.handler}\n{ep.description}"
            })
            edges.append({
                "from": frontend_id,
                "to": node_id,
                "label": "请求",
                "arrows": "to"
            })
            node_id += 1
        
        # 服务层节点
        service_nodes = {}
        for key, service in self.services.items():
            svc_id = node_id
            service_nodes[key] = svc_id
            nodes.append({
                "id": node_id,
                "label": f"{service.class_name}\n.{service.name}",
                "group": "service",
                "level": 2,
                "title": f"{service.class_name}.{service.name}\nDB: {', '.join(service.db_operations) if service.db_operations else '无'}"
            })
            node_id += 1
        
        # 数据库节点
        db_id = node_id
        nodes.append({
            "id": node_id,
            "label": "🗄️ 数据库",
            "group": "database",
            "level": 3
        })
        node_id += 1
        
        # 连接API到服务
        for flow in self.data_flows:
            api_id = api_nodes.get(flow.endpoint)
            if api_id and flow.service_calls:
                for call in flow.service_calls:
                    for key, svc_id in service_nodes.items():
                        if call in key:
                            edges.append({
                                "from": api_id,
                                "to": svc_id,
                                "label": "调用",
                                "arrows": "to"
                            })
        
        # 连接服务到数据库
        for key, svc_id in service_nodes.items():
            service = self.services.get(key)
            if service and service.db_operations:
                edges.append({
                    "from": svc_id,
                    "to": db_id,
                    "label": ", ".join(service.db_operations[:2]),
                    "arrows": "to"
                })
        
        # 生成HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} - API数据流图</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #eee; }}
        
        .container {{ display: flex; height: 100vh; }}
        
        .sidebar {{
            width: 320px; background: #16213e; padding: 20px;
            overflow-y: auto; border-right: 1px solid #0f3460;
        }}
        .sidebar h1 {{
            font-size: 20px; margin-bottom: 20px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}
        
        .filter-section {{ margin-bottom: 20px; }}
        .filter-section h3 {{ color: #888; font-size: 14px; margin-bottom: 10px; }}
        
        .filter-btn {{
            display: inline-block; padding: 6px 12px; margin: 4px;
            background: #0f3460; border: 1px solid #1a1a4e;
            border-radius: 6px; color: #eee; cursor: pointer;
            font-size: 12px; transition: all 0.2s;
        }}
        .filter-btn:hover {{ background: #1a1a4e; }}
        .filter-btn.active {{ background: #667eea; border-color: #667eea; }}
        
        .search-box {{
            width: 100%; padding: 10px; margin-bottom: 15px;
            background: #0f3460; border: 1px solid #1a1a4e;
            border-radius: 8px; color: #eee; font-size: 14px;
        }}
        .search-box:focus {{ outline: none; border-color: #667eea; }}
        
        .endpoint-list {{ max-height: 400px; overflow-y: auto; }}
        .endpoint-item {{
            padding: 10px; margin-bottom: 5px; background: #0f3460;
            border-radius: 6px; cursor: pointer; transition: all 0.2s;
            font-size: 13px;
        }}
        .endpoint-item:hover {{ background: #1a1a4e; }}
        .endpoint-item.active {{ background: #667eea; }}
        .endpoint-method {{
            display: inline-block; padding: 2px 6px; border-radius: 4px;
            font-size: 11px; font-weight: bold; margin-right: 8px;
        }}
        .method-GET {{ background: #4CAF50; }}
        .method-POST {{ background: #2196F3; }}
        .method-PUT {{ background: #FF9800; }}
        .method-DELETE {{ background: #f44336; }}
        
        .main {{ flex: 1; position: relative; }}
        #network {{ width: 100%; height: 100%; }}
        
        .detail-panel {{
            position: absolute; top: 20px; right: 20px;
            width: 420px; background: rgba(22, 33, 62, 0.98);
            border-radius: 12px; padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
            border: 1px solid rgba(102, 126, 234, 0.3);
            display: none; max-height: 85vh; overflow-y: auto;
        }}
        .detail-panel::-webkit-scrollbar {{ width: 6px; }}
        .detail-panel::-webkit-scrollbar-track {{ background: transparent; }}
        .detail-panel::-webkit-scrollbar-thumb {{ background: #667eea; border-radius: 3px; }}
        .detail-panel.visible {{ display: block; }}
        .detail-panel h3 {{ color: #667eea; margin-bottom: 15px; font-size: 16px; }}
        .detail-row {{ padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        .detail-label {{ color: #888; font-size: 12px; }}
        .detail-value {{ color: #eee; font-size: 14px; margin-top: 4px; }}
        .close-btn {{
            position: absolute; top: 10px; right: 10px;
            background: none; border: none; color: #888;
            cursor: pointer; font-size: 18px;
        }}
        
        .legend {{
            position: absolute; bottom: 20px; left: 20px;
            background: rgba(22, 33, 62, 0.95); border-radius: 8px;
            padding: 15px; font-size: 12px;
        }}
        .legend-item {{ display: flex; align-items: center; margin-bottom: 5px; }}
        .legend-color {{ width: 12px; height: 12px; border-radius: 3px; margin-right: 8px; }}
        
        .stats {{
            position: absolute; top: 20px; left: 20px;
            background: rgba(22, 33, 62, 0.95); border-radius: 8px;
            padding: 15px; font-size: 12px;
        }}
        .stats-row {{ display: flex; gap: 15px; }}
        .stat {{ text-align: center; }}
        .stat .num {{ font-size: 24px; font-weight: bold; color: #667eea; }}
        .stat .label {{ color: #888; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>📊 {project_name}</h1>
            
            <input type="text" class="search-box" id="searchInput" placeholder="🔍 搜索接口...">
            
            <div class="filter-section">
                <h3>请求方法</h3>
                <button class="filter-btn active" data-method="ALL">全部</button>
                <button class="filter-btn" data-method="GET">GET</button>
                <button class="filter-btn" data-method="POST">POST</button>
                <button class="filter-btn" data-method="PUT">PUT</button>
                <button class="filter-btn" data-method="DELETE">DELETE</button>
            </div>
            
            <div class="filter-section">
                <h3>模块</h3>
                <div id="moduleFilters"></div>
            </div>
            
            <div class="endpoint-list" id="endpointList"></div>
        </div>
        
        <div class="main">
            <div id="network"></div>
            
            <div id="loadingBar" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1000; background: rgba(22, 33, 62, 0.95); padding: 30px; border-radius: 12px; text-align: center; min-width: 300px;">
                <div style="margin-bottom: 15px; font-size: 16px; color: #667eea;">📊 正在加载数据流图...</div>
                <div style="width: 100%; height: 8px; background: #0f3460; border-radius: 4px; overflow: hidden;">
                    <div id="loadingProgress" style="width: 0%; height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); transition: width 0.1s;"></div>
                </div>
                <div id="loadingText" style="margin-top: 10px; color: #888; font-size: 14px;">准备加载...</div>
            </div>
            
            <div class="stats">
                <div class="stats-row">
                    <div class="stat">
                        <div class="num">{len(self.endpoints)}</div>
                        <div class="label">API接口</div>
                    </div>
                    <div class="stat">
                        <div class="num">{len(self.services)}</div>
                        <div class="label">服务方法</div>
                    </div>
                    <div class="stat">
                        <div class="num">{len(self.models)}</div>
                        <div class="label">数据模型</div>
                    </div>
                </div>
            </div>
            
            <div class="detail-panel" id="detailPanel">
                <button class="close-btn" onclick="closeDetail()">×</button>
                <h3 id="detailTitle">详情</h3>
                <div id="detailContent"></div>
            </div>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #61dafb"></div>
                    <span>前端</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #4CAF50"></div>
                    <span>API接口</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #2196F3"></div>
                    <span>服务层</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #FF9800"></div>
                    <span>数据库</span>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const nodesData = {repr(nodes)};
        const edgesData = {repr(edges)};
        
        const endpoints = {repr([{
            'method': ep.method,
            'path': ep.path,
            'handler': ep.handler,
            'description': ep.description[:200] if ep.description else '',
            'file': Path(ep.file_path).stem,
            'request_body': ep.request_body or '',
            'dependencies': ep.dependencies[:3] if ep.dependencies else [],
            'service_calls': next((f.service_calls for f in self.data_flows if f.endpoint == ep.path), []),
            'db_operations': next((f.db_operations for f in self.data_flows if f.endpoint == ep.path), [])
        } for ep in self.endpoints])};
        
        const typeColors = {{
            'frontend': {{ background: '#61dafb', border: '#21a0c4' }},
            'api': {{ background: '#4CAF50', border: '#388E3C' }},
            'service': {{ background: '#2196F3', border: '#1565C0' }},
            'database': {{ background: '#FF9800', border: '#F57C00' }}
        }};
        
        // 创建空的DataSet
        const nodes = new vis.DataSet();
        const edges = new vis.DataSet();
        
        const container = document.getElementById('network');
        const network = new vis.Network(container, {{ nodes, edges }}, {{
            layout: {{
                hierarchical: {{
                    direction: 'LR',
                    sortMethod: 'directed',
                    levelSeparation: 250,
                    nodeSpacing: 150
                }}
            }},
            physics: {{ enabled: false }},
            interaction: {{
                hover: true,
                tooltipDelay: 200,
                zoomView: true,
                dragView: true
            }},
            nodes: {{
                borderWidth: 2,
                shadow: true
            }}
        }});
        
        // 逐个加载节点和边
        const loadingProgress = document.getElementById('loadingProgress');
        const loadingText = document.getElementById('loadingText');
        let loadedNodes = 0;
        let loadedEdges = 0;
        
        function loadNextNode() {{
            if (loadedNodes < nodesData.length) {{
                const n = nodesData[loadedNodes];
                nodes.add({{
                    ...n,
                    color: typeColors[n.group] || typeColors.api,
                    font: {{ color: '#fff', size: 12 }},
                    shape: n.group === 'database' ? 'database' : (n.group === 'frontend' ? 'icon' : 'box'),
                    margin: 10,
                    widthConstraint: {{ maximum: 200 }}
                }});
                loadedNodes++;
                loadingText.textContent = `加载节点: ${{loadedNodes}}/${{nodesData.length}}`;
                loadingProgress.style.width = `${{(loadedNodes / nodesData.length) * 100}}%`;
                
                // 加载相关的边
                const nodeId = n.id;
                edgesData.filter(e => e.from === nodeId || e.to === nodeId).forEach(e => {{
                    if (!edges.get().find(existing => existing.from === e.from && existing.to === e.to)) {{
                        edges.add({{
                            ...e,
                            color: {{ color: '#666', highlight: '#667eea' }},
                            font: {{ color: '#888', size: 10 }},
                            smooth: {{ type: 'curvedCW', roundness: 0.2 }}
                        }});
                        loadedEdges++;
                    }}
                }});
                
                // 继续加载下一个
                setTimeout(loadNextNode, 50);
            }} else {{
                // 加载完成
                loadingText.textContent = '加载完成';
                setTimeout(() => {{
                    document.getElementById('loadingBar').style.display = 'none';
                }}, 1000);
                
                // 适配视图
                network.fit({{ animation: true }});
            }}
        }}
        
        // 开始加载
        setTimeout(loadNextNode, 100);
        
        // 填充接口列表
        const endpointList = document.getElementById('endpointList');
        const moduleFilters = document.getElementById('moduleFilters');
        const modules = [...new Set(endpoints.map(e => e.file))];
        
        modules.forEach(m => {{
            const btn = document.createElement('button');
            btn.className = 'filter-btn';
            btn.dataset.module = m;
            btn.textContent = m;
            btn.onclick = () => {{
                btn.classList.toggle('active');
                filterEndpoints();
            }};
            moduleFilters.appendChild(btn);
        }});
        
        function renderEndpoints(filteredEndpoints) {{
            endpointList.innerHTML = filteredEndpoints.map((e, i) => `
                <div class="endpoint-item" data-index="${{i}}" onclick="highlightEndpoint(${{i}})">
                    <span class="endpoint-method method-${{e.method}}">${{e.method}}</span>
                    <span>${{e.path}}</span>
                </div>
            `).join('');
        }}
        
        renderEndpoints(endpoints);
        
        // 搜索
        document.getElementById('searchInput').addEventListener('input', (e) => {{
            const query = e.target.value.toLowerCase();
            const filtered = endpoints.filter(ep => 
                ep.path.toLowerCase().includes(query) || 
                ep.handler.toLowerCase().includes(query) ||
                ep.description.toLowerCase().includes(query)
            );
            renderEndpoints(filtered);
        }});
        
        // 方法过滤
        document.querySelectorAll('.filter-btn[data-method]').forEach(btn => {{
            btn.onclick = () => {{
                document.querySelectorAll('.filter-btn[data-method]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                filterEndpoints();
            }};
        }});
        
        function filterEndpoints() {{
            const method = document.querySelector('.filter-btn[data-method].active')?.dataset.method || 'ALL';
            const activeModules = [...document.querySelectorAll('.filter-btn[data-module].active')].map(b => b.dataset.module);
            
            let filtered = endpoints;
            if (method !== 'ALL') {{
                filtered = filtered.filter(e => e.method === method);
            }}
            if (activeModules.length > 0) {{
                filtered = filtered.filter(e => activeModules.includes(e.file));
            }}
            
            renderEndpoints(filtered);
        }}
        
        // 高亮接口
        function highlightEndpoint(index) {{
            const ep = endpoints[index];
            const nodeId = nodesData.find(n => n.label?.includes(ep.path))?.id;
            
            if (nodeId !== undefined) {{
                network.selectNodes([nodeId]);
                network.focus(nodeId, {{ scale: 1.5, animation: true }});
                
                // 显示详情
                showDetail(ep);
                
                // 高亮相关节点
                const connected = network.getConnectedNodes(nodeId);
                const allNodes = nodes.getIds();
                allNodes.forEach(id => {{
                    if (id === nodeId || connected.includes(id)) {{
                        nodes.update({{ id, opacity: 1 }});
                    }} else {{
                        nodes.update({{ id, opacity: 0.2 }});
                    }}
                }});
            }}
        }}
        
        function showDetail(ep) {{
            const panel = document.getElementById('detailPanel');
            const title = document.getElementById('detailTitle');
            const content = document.getElementById('detailContent');
            
            title.textContent = `${{ep.method}} ${{ep.path}}`;
            
            let html = `
                <div class="detail-row">
                    <div class="detail-label">处理函数</div>
                    <div class="detail-value">${{ep.handler}}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">模块</div>
                    <div class="detail-value">${{ep.file}}</div>
                </div>
            `;
            
            if (ep.description) {{
                html += `
                    <div class="detail-row">
                        <div class="detail-label">描述</div>
                        <div class="detail-value">${{ep.description}}</div>
                    </div>
                `;
            }}
            
            if (ep.request_body) {{
                html += `
                    <div class="detail-row">
                        <div class="detail-label">请求体</div>
                        <div class="detail-value">${{ep.request_body}}</div>
                    </div>
                `;
            }}
            
            if (ep.dependencies && ep.dependencies.length > 0) {{
                html += `
                    <div class="detail-row">
                        <div class="detail-label">依赖注入</div>
                        <div class="detail-value">${{ep.dependencies.join(', ')}}</div>
                    </div>
                `;
            }}
            
            // 数据流详情
            html += `
                <div style="margin-top: 20px; padding-top: 15px; border-top: 2px solid #667eea;">
                    <div class="detail-label" style="font-size: 14px; font-weight: bold; color: #667eea; margin-bottom: 15px;">📊 数据流</div>
                    
                    <div style="background: #0f3460; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                        <div style="display: flex; align-items: center; margin-bottom: 10px;">
                            <div style="width: 30px; height: 30px; background: #61dafb; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; font-size: 14px;">🌐</div>
                            <div>
                                <div style="font-weight: bold; font-size: 13px;">前端请求</div>
                                <div style="color: #888; font-size: 12px;">发起 ${{ep.method}} 请求</div>
                            </div>
                        </div>
                        <div style="text-align: center; color: #667eea; font-size: 18px; margin: 5px 0;">↓</div>
                        <div style="background: #1a1a4e; border-radius: 6px; padding: 10px; font-family: monospace; font-size: 12px;">
                            ${{ep.method}} ${{ep.path}}
                        </div>
                    </div>
                    
                    <div style="text-align: center; color: #667eea; font-size: 18px; margin: 10px 0;">↓</div>
                    
                    <div style="background: #0f3460; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                        <div style="display: flex; align-items: center; margin-bottom: 10px;">
                            <div style="width: 30px; height: 30px; background: #4CAF50; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; font-size: 14px;">📦</div>
                            <div>
                                <div style="font-weight: bold; font-size: 13px;">路由处理</div>
                                <div style="color: #888; font-size: 12px;">${{ep.file}}.py</div>
                            </div>
                        </div>
                        <div style="background: #1a1a4e; border-radius: 6px; padding: 10px; font-family: monospace; font-size: 12px;">
                            async def ${{ep.handler}}()
                        </div>
                    </div>
            `;
            
            // 服务层调用
            if (ep.service_calls && ep.service_calls.length > 0) {{
                html += `
                    <div style="text-align: center; color: #667eea; font-size: 18px; margin: 10px 0;">↓</div>
                    
                    <div style="background: #0f3460; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                        <div style="display: flex; align-items: center; margin-bottom: 10px;">
                            <div style="width: 30px; height: 30px; background: #2196F3; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; font-size: 14px;">⚙️</div>
                            <div>
                                <div style="font-weight: bold; font-size: 13px;">服务层</div>
                                <div style="color: #888; font-size: 12px;">业务逻辑处理</div>
                            </div>
                        </div>
                        <div style="background: #1a1a4e; border-radius: 6px; padding: 10px;">
                `;
                
                ep.service_calls.forEach(call => {{
                    html += `<div style="font-family: monospace; font-size: 12px; padding: 3px 0;">• ${{call}}()</div>`;
                }});
                
                html += `
                        </div>
                    </div>
                `;
            }}
            
            // 数据库操作
            if (ep.db_operations && ep.db_operations.length > 0) {{
                html += `
                    <div style="text-align: center; color: #667eea; font-size: 18px; margin: 10px 0;">↓</div>
                    
                    <div style="background: #0f3460; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                        <div style="display: flex; align-items: center; margin-bottom: 10px;">
                            <div style="width: 30px; height: 30px; background: #FF9800; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; font-size: 14px;">🗄️</div>
                            <div>
                                <div style="font-weight: bold; font-size: 13px;">数据库</div>
                                <div style="color: #888; font-size: 12px;">数据持久化</div>
                            </div>
                        </div>
                        <div style="background: #1a1a4e; border-radius: 6px; padding: 10px;">
                `;
                
                const uniqueOps = [...new Set(ep.db_operations)];
                uniqueOps.forEach(op => {{
                    html += `<div style="font-family: monospace; font-size: 12px; padding: 3px 0;">• ${{op}}</div>`;
                }});
                
                html += `
                        </div>
                    </div>
                `;
            }}
            
            // 返回响应
            html += `
                    <div style="text-align: center; color: #667eea; font-size: 18px; margin: 10px 0;">↓</div>
                    
                    <div style="background: #0f3460; border-radius: 8px; padding: 15px;">
                        <div style="display: flex; align-items: center;">
                            <div style="width: 30px; height: 30px; background: #61dafb; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; font-size: 14px;">🌐</div>
                            <div>
                                <div style="font-weight: bold; font-size: 13px;">返回响应</div>
                                <div style="color: #888; font-size: 12px;">JSON Response</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            content.innerHTML = html;
            panel.classList.add('visible');
        }}
        
        function closeDetail() {{
            document.getElementById('detailPanel').classList.remove('visible');
            nodes.getIds().forEach(id => nodes.update({{ id, opacity: 1 }}));
        }}
        
        // 点击空白处重置
        network.on('click', (params) => {{
            if (params.nodes.length === 0) {{
                closeDetail();
            }}
        }});
    </script>
</body>
</html>"""
        
        return html
