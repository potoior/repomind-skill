"""API流程分析器 - 分析接口调用流程并生成流程图"""

import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field


@dataclass
class FunctionInfo:
    """函数信息"""
    name: str
    file_path: str
    class_name: Optional[str] = None
    calls: List[str] = field(default_factory=list)
    description: Optional[str] = None
    line_number: int = 0


@dataclass
class APIEndpoint:
    """API端点"""
    method: str
    path: str
    handler: str
    file_path: str
    description: Optional[str] = None
    steps: List[str] = field(default_factory=list)


class FlowAnalyzer:
    """流程分析器"""
    
    def __init__(self):
        self.functions: Dict[str, FunctionInfo] = {}
        self.api_endpoints: List[APIEndpoint] = []
        self.call_graph: Dict[str, List[str]] = {}
    
    def analyze_code_files(self, code_files: List[tuple]) -> None:
        """分析代码文件"""
        for file_path, content in code_files:
            self._extract_functions(file_path, content)
            self._extract_api_endpoints(file_path, content)
        
        self._build_call_graph()
        self._analyze_api_flows()
    
    def _extract_functions(self, file_path: str, content: str) -> None:
        """提取函数信息"""
        lines = content.split('\n')
        current_class = None
        
        for i, line in enumerate(lines, 1):
            # 检测类定义
            class_match = re.match(r'class\s+(\w+)', line)
            if class_match:
                current_class = class_match.group(1)
            
            # 检测函数定义 (支持async def)
            func_match = re.match(r'\s*(?:async\s+)?def\s+(\w+)\s*\(', line)
            if func_match:
                func_name = func_match.group(1)
                full_name = f"{current_class}.{func_name}" if current_class else func_name
                
                # 提取函数体中的调用
                func_body = self._extract_function_body(lines, i - 1)
                calls = self._extract_function_calls(func_body)
                
                # 提取docstring
                desc = self._extract_docstring(func_body)
                
                func_info = FunctionInfo(
                    name=func_name,
                    file_path=file_path,
                    class_name=current_class,
                    calls=calls,
                    description=desc,
                    line_number=i
                )
                
                self.functions[full_name] = func_info
                self.functions[func_name] = func_info  # 也用短名称存储
    
    def _extract_function_body(self, lines: List[str], start_idx: int) -> str:
        """提取函数体"""
        if start_idx >= len(lines):
            return ""
        
        # 获取函数定义的缩进级别
        indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
        
        body_lines = []
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip():  # 空行
                body_lines.append(line)
                continue
            
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent and line.strip():
                break
            
            body_lines.append(line)
        
        return '\n'.join(body_lines)
    
    def _extract_function_calls(self, body: str) -> List[str]:
        """提取函数调用"""
        calls = []
        
        # 匹配 self.method() 或 function()
        patterns = [
            r'self\.(\w+)\s*\(',  # self.method()
            r'(\w+)\s*\(',        # function()
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, body)
            for match in matches:
                if match not in ['if', 'for', 'while', 'return', 'print', 'len', 'str', 'int', 'list', 'dict', 'set']:
                    calls.append(match)
        
        return list(set(calls))
    
    def _extract_docstring(self, body: str) -> Optional[str]:
        """提取docstring"""
        match = re.search(r'"""(.*?)"""', body, re.DOTALL)
        if match:
            return match.group(1).strip().split('\n')[0]
        return None
    
    def _extract_api_endpoints(self, file_path: str, content: str) -> None:
        """提取API端点"""
        # Python装饰器模式 (Flask/FastAPI)
        patterns = [
            # FastAPI: @app.get("/path")
            r'@app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            # Flask: @app.route("/path", methods=["GET"])
            r'@app\.route\s*\(\s*["\']([^"\']+)["\'].*methods\s*=\s*\[["\'](\w+)["\']',
            # 路由装饰器
            r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                if len(match.groups()) == 2:
                    method = match.group(1).upper()
                    path = match.group(2)
                    
                    # 找到对应的处理函数
                    func_name = self._find_handler_after_decorator(content, match.end())
                    
                    endpoint = APIEndpoint(
                        method=method,
                        path=path,
                        handler=func_name or "unknown",
                        file_path=file_path
                    )
                    self.api_endpoints.append(endpoint)
        
        # Express.js模式
        express_pattern = r'app\.(get|post|put|delete)\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(express_pattern, content):
            endpoint = APIEndpoint(
                method=match.group(1).upper(),
                path=match.group(2),
                handler="handler",
                file_path=file_path
            )
            self.api_endpoints.append(endpoint)
    
    def _find_handler_after_decorator(self, content: str, pos: int) -> Optional[str]:
        """找到装饰器后面的函数名"""
        remaining = content[pos:]
        match = re.search(r'def\s+(\w+)', remaining)
        return match.group(1) if match else None
    
    def _build_call_graph(self) -> None:
        """构建调用图"""
        for name, func in self.functions.items():
            if '.' in name:  # 只处理完整名称
                self.call_graph[name] = func.calls
    
    def _analyze_api_flows(self) -> None:
        """分析API流程"""
        for endpoint in self.api_endpoints:
            handler = endpoint.handler
            steps = self._trace_call_chain(handler, set())
            endpoint.steps = steps
    
    # 需要过滤的内置/外部调用
    FILTERED_CALLS = {
        'if', 'for', 'while', 'return', 'print', 'len', 'str', 'int', 'list', 'dict', 'set',
        'raise', 'HTTPException', 'None', 'True', 'False',
        # 常见的方法调用
        'close', 'commit', 'cursor', 'execute', 'fetchall', 'fetchone',
        'encode', 'decode', 'hexdigest', 'sha256', 'connect',
        'append', 'extend', 'remove', 'pop', 'insert',
        'get', 'post', 'put', 'delete', 'patch',
        'json', 'strip', 'split', 'join', 'replace', 'format',
        'keys', 'values', 'items', 'update',
        'upper', 'lower', 'capitalize', 'title',
        'isdigit', 'isalpha', 'isalnum',
    }
    
    def _trace_call_chain(self, func_name: str, visited: Set[str], depth: int = 0) -> List[str]:
        """追踪调用链"""
        if depth > 3 or func_name in visited:
            return []
        
        visited.add(func_name)
        steps = [func_name]
        
        # 查找函数信息
        func_info = self.functions.get(func_name)
        if not func_info:
            # 尝试短名称
            for key, info in self.functions.items():
                if key.endswith(f".{func_name}") or key == func_name:
                    func_info = info
                    break
        
        if not func_info:
            return steps
        
        # 递归追踪调用
        for call in func_info.calls:
            # 跳过内置函数和常见方法
            if call in self.FILTERED_CALLS or call.startswith('_'):
                continue
            
            # 尝试不同的名称格式
            full_name = None
            if func_info.class_name:
                full_name = f"{func_info.class_name}.{call}"
            
            # 查找函数
            found = False
            for possible_name in [full_name, call]:
                if possible_name and possible_name in self.functions:
                    sub_steps = self._trace_call_chain(possible_name, visited, depth + 1)
                    steps.extend(sub_steps)
                    found = True
                    break
        
        return steps
    
    def generate_mermaid_flowchart(self, endpoint_idx: int = None) -> str:
        """生成Mermaid流程图"""
        if endpoint_idx is not None and endpoint_idx < len(self.api_endpoints):
            endpoints = [self.api_endpoints[endpoint_idx]]
        else:
            endpoints = self.api_endpoints
        
        if not endpoints:
            return "graph TD\n    A[No API endpoints found]"
        
        mermaid = "graph TD\n"
        mermaid += "    %% 样式定义\n"
        mermaid += "    classDef apiNode fill:#4CAF50,stroke:#388E3C,color:white\n"
        mermaid += "    classDef funcNode fill:#2196F3,stroke:#1565C0,color:white\n"
        mermaid += "    classDef dbNode fill:#FF9800,stroke:#EF6C00,color:white\n\n"
        
        for endpoint in endpoints:
            # 创建API入口节点
            api_id = f"API_{endpoint.method}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}"
            api_label = f"{endpoint.method} {endpoint.path}"
            mermaid += f"    {api_id}[\"🌐 {api_label}\"]:::apiNode\n"
            
            # 创建流程步骤
            prev_id = api_id
            for i, step in enumerate(endpoint.steps):
                step_id = f"{api_id}_step{i}"
                step_info = self.functions.get(step)
                
                if step_info:
                    desc = step_info.description or step
                    file_info = f"📁 {step_info.file_path}"
                    mermaid += f"    {step_id}[\"📦 {step}\\n{desc}\\n{file_info}\"]:::funcNode\n"
                else:
                    mermaid += f"    {step_id}[\"📦 {step}\"]:::funcNode\n"
                
                mermaid += f"    {prev_id} --> {step_id}\n"
                prev_id = step_id
            
            # 添加结束节点
            end_id = f"{api_id}_end"
            mermaid += f"    {end_id}[\"✅ 返回响应\"]:::apiNode\n"
            mermaid += f"    {prev_id} --> {end_id}\n\n"
        
        return mermaid
    
    def generate_all_flowcharts(self) -> Dict[str, str]:
        """为每个API生成单独的流程图"""
        flowcharts = {}
        
        for i, endpoint in enumerate(self.api_endpoints):
            key = f"{endpoint.method} {endpoint.path}"
            flowcharts[key] = self.generate_mermaid_flowchart(i)
        
        return flowcharts
    
    def get_api_summary(self) -> List[Dict]:
        """获取API摘要"""
        summaries = []
        
        for endpoint in self.api_endpoints:
            summary = {
                "method": endpoint.method,
                "path": endpoint.path,
                "handler": endpoint.handler,
                "file": endpoint.file_path,
                "steps_count": len(endpoint.steps),
                "steps": endpoint.steps
            }
            summaries.append(summary)
        
        return summaries


def analyze_project_flows(code_files: List[tuple]) -> FlowAnalyzer:
    """分析项目流程"""
    analyzer = FlowAnalyzer()
    analyzer.analyze_code_files(code_files)
    return analyzer