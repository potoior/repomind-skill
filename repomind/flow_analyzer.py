"""流程分析器 - 分析API端点和函数调用链"""

import re
from typing import List, Dict, Set, Optional
from pydantic import BaseModel, Field
from .renderers import render_mermaid_flowchart, render_call_chain_mermaid


class FunctionInfo(BaseModel):
    """函数信息"""
    name: str
    file_path: str
    class_name: Optional[str] = None
    calls: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    line_number: int = 0


class APIEndpoint(BaseModel):
    """API端点"""
    method: str
    path: str
    handler: str
    file_path: str
    description: Optional[str] = None
    steps: List[str] = Field(default_factory=list)


class CallChain(BaseModel):
    """函数调用链"""
    entry_point: str
    file_path: str
    description: Optional[str] = None
    steps: List[str] = Field(default_factory=list)
    depth: int = 0


class FlowAnalyzer:
    """流程分析器"""
    
    def __init__(self):
        self.functions: Dict[str, FunctionInfo] = {}
        self.api_endpoints: List[APIEndpoint] = []
        self.call_chains: List[CallChain] = []
        self.call_graph: Dict[str, List[str]] = {}
    
    def analyze_code_files(self, code_files: List[tuple]) -> None:
        """分析代码文件"""
        for file_path, content in code_files:
            self._extract_functions(file_path, content)
            self._extract_api_endpoints(file_path, content)
        
        self._build_call_graph()
        self._analyze_api_flows()
        self._analyze_function_chains()
    
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
        
        # Express.js模式 (JavaScript文件中没有@前缀)
        express_pattern = r'(?<!@)app\.(get|post|put|delete)\s*\(\s*["\']([^"\']+)["\']'
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

    def _analyze_function_chains(self) -> None:
        """分析函数调用链 - 找到入口函数并追踪调用链"""
        # 找到所有被调用过的函数名
        called_by: Dict[str, Set[str]] = {}
        for name, func in self.functions.items():
            if '.' not in name:
                continue
            for call in func.calls:
                if call in self.FILTERED_CALLS or call.startswith('_'):
                    continue
                called_by.setdefault(call, set()).add(name)

        # 入口函数：公开方法、有调用链、不是纯被调用的叶子
        entry_candidates = []
        for name, func in self.functions.items():
            if '.' not in name:
                continue
            if func.name.startswith('_'):
                continue
            # 有实际的下游调用（支持短名称解析）
            def _resolve_call(call_name: str) -> bool:
                if call_name in self.functions:
                    return True
                if func.class_name:
                    full = f"{func.class_name}.{call_name}"
                    if full in self.functions:
                        return True
                for key in self.functions:
                    if key.endswith(f".{call_name}"):
                        return True
                return False
            
            real_calls = [c for c in func.calls
                          if c not in self.FILTERED_CALLS and not c.startswith('_')
                          and _resolve_call(c)]
            if not real_calls:
                continue
            # 计算调用链深度
            chain = self._trace_call_chain(name, set(), max_depth=5)
            if len(chain) >= 2:
                entry_candidates.append((name, func, chain))

        # 按调用链长度排序，取前 20 个
        entry_candidates.sort(key=lambda x: len(x[2]), reverse=True)
        seen = set()
        for name, func, chain in entry_candidates[:20]:
            if name in seen:
                continue
            seen.add(name)
            self.call_chains.append(CallChain(
                entry_point=name,
                file_path=func.file_path,
                description=func.description,
                steps=chain,
                depth=len(chain),
            ))
    
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
    
    def _trace_call_chain(self, func_name: str, visited: Set[str], depth: int = 0, max_depth: int = 3) -> List[str]:
        """追踪调用链"""
        if depth > max_depth or func_name in visited:
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
        """生成Mermaid流程图（API端点）"""
        return render_mermaid_flowchart(self.api_endpoints, self.functions, endpoint_idx)
    
    def generate_all_flowcharts(self) -> Dict[str, str]:
        """为每个API和调用链生成单独的流程图"""
        flowcharts = {}
        
        for i, endpoint in enumerate(self.api_endpoints):
            key = f"{endpoint.method} {endpoint.path}"
            flowcharts[key] = self.generate_mermaid_flowchart(i)
        
        for i, chain in enumerate(self.call_chains):
            key = f"call:{chain.entry_point}"
            flowcharts[key] = render_call_chain_mermaid(chain, self.functions)
        
        return flowcharts

    def generate_call_chain_flowchart(self, chain_idx: int = None) -> str:
        """生成函数调用链流程图"""
        if chain_idx is not None and 0 <= chain_idx < len(self.call_chains):
            return render_call_chain_mermaid(self.call_chains[chain_idx], self.functions)
        # 生成所有调用链的合并图
        mermaid = "graph TD\n"
        mermaid += "    classDef entryNode fill:#4CAF50,stroke:#388E3C,color:white\n"
        mermaid += "    classDef funcNode fill:#2196F3,stroke:#1565C0,color:white\n\n"
        for chain in self.call_chains[:10]:
            mermaid += render_call_chain_mermaid(chain, self.functions, standalone=False)
        return mermaid
    
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