import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from repomind.flow_analyzer import FlowAnalyzer, FunctionInfo, APIEndpoint, CallChain, analyze_project_flows


def test_extract_functions():
    code = '''class UserService:
    def get_user(self):
        """Get user by ID"""
        user = self._fetch_from_db()
        return user

    def _fetch_from_db(self):
        return {}

def validate_input(data):
    """Validate input data"""
    return True
'''
    analyzer = FlowAnalyzer()
    analyzer._extract_functions("app/service.py", code)

    assert "UserService.get_user" in analyzer.functions
    assert "validate_input" in analyzer.functions

    func = analyzer.functions["UserService.get_user"]
    assert func.description == "Get user by ID"
    assert func.file_path == "app/service.py"
    assert func.class_name == "UserService"


def test_extract_api_endpoints_fastapi():
    code = '''from fastapi import FastAPI
app = FastAPI()

@app.get("/users")
def list_users():
    """List all users"""
    return []

@app.post("/items")
def create_item(item: dict):
    """Create an item"""
    return item
'''
    analyzer = FlowAnalyzer()
    analyzer._extract_api_endpoints("app/main.py", code)

    methods = {(e.method, e.path) for e in analyzer.api_endpoints}
    assert ("GET", "/users") in methods
    assert ("POST", "/items") in methods


def test_extract_api_endpoints_express():
    code = '''const express = require('express');
const app = express();

app.get('/api/items', (req, res) => {
    res.json([]);
});

app.post('/api/items', (req, res) => {
    res.json(req.body);
});
'''
    analyzer = FlowAnalyzer()
    analyzer._extract_api_endpoints("server.js", code)

    assert len(analyzer.api_endpoints) == 2
    paths = {e.path for e in analyzer.api_endpoints}
    assert "/api/items" in paths


def test_trace_call_chain():
    analyzer = FlowAnalyzer()
    analyzer.functions = {
        "Service.handle": FunctionInfo(
            name="handle", file_path="app.py", class_name="Service",
            calls=["validate", "save"], description="Handle request"
        ),
        "validate": FunctionInfo(
            name="validate", file_path="app.py", calls=[], description="Validate"
        ),
        "save": FunctionInfo(
            name="save", file_path="app.py", calls=["persist"], description="Save to db"
        ),
        "persist": FunctionInfo(
            name="persist", file_path="db.py", calls=[], description="Persist data"
        ),
    }

    steps = analyzer._trace_call_chain("Service.handle", set())
    assert "Service.handle" in steps
    assert "validate" in steps
    assert "save" in steps
    assert "persist" in steps


def test_trace_call_chain_depth_limit():
    analyzer = FlowAnalyzer()
    analyzer.functions = {
        "a": FunctionInfo(name="a", file_path="x.py", calls=["b"]),
        "b": FunctionInfo(name="b", file_path="x.py", calls=["c"]),
        "c": FunctionInfo(name="c", file_path="x.py", calls=["d"]),
        "d": FunctionInfo(name="d", file_path="x.py", calls=["e"]),
        "e": FunctionInfo(name="e", file_path="x.py", calls=[]),
    }

    steps = analyzer._trace_call_chain("a", set())
    # depth limit is 3, so "e" (depth 4) should not be reached
    assert "a" in steps
    assert "e" not in steps


def test_generate_mermaid_flowchart():
    analyzer = FlowAnalyzer()
    analyzer.api_endpoints = [
        APIEndpoint(method="GET", path="/health", handler="health_check", file_path="app.py", steps=["health_check"]),
    ]
    analyzer.functions = {
        "health_check": FunctionInfo(name="health_check", file_path="app.py", calls=[], description="Health check"),
    }

    mermaid = analyzer.generate_mermaid_flowchart(0)
    assert "graph TD" in mermaid
    assert "GET /health" in mermaid
    assert "health_check" in mermaid


def test_analyze_project_flows_integration():
    code_files = [
        ("app.py", '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/items")
def list_items():
    """List items"""
    return fetch_items()

def fetch_items():
    """Fetch from db"""
    return []
'''),
    ]

    analyzer = analyze_project_flows(code_files)
    assert len(analyzer.api_endpoints) >= 1

    endpoint = analyzer.api_endpoints[0]
    assert endpoint.method == "GET"
    assert endpoint.path == "/items"


def test_function_info_pydantic():
    fi = FunctionInfo(name="test", file_path="x.py", calls=["a", "b"])
    assert fi.name == "test"
    assert fi.calls == ["a", "b"]
    assert fi.line_number == 0
    assert fi.description is None


def test_api_endpoint_pydantic():
    ep = APIEndpoint(method="GET", path="/test", handler="handler", file_path="x.py")
    d = ep.model_dump()
    assert d["method"] == "GET"
    assert d["steps"] == []


def test_call_chain_pydantic():
    chain = CallChain(entry_point="Service.handle", file_path="app.py", steps=["a", "b"], depth=2)
    assert chain.entry_point == "Service.handle"
    assert chain.steps == ["a", "b"]
    assert chain.depth == 2
    assert chain.description is None


def test_analyze_function_chains():
    analyzer = FlowAnalyzer()
    analyzer.functions = {
        "Service.process": FunctionInfo(
            name="process", file_path="app.py", class_name="Service",
            calls=["validate", "transform"], description="Process data"
        ),
        "Service.validate": FunctionInfo(
            name="validate", file_path="app.py", class_name="Service",
            calls=["check_format"], description="Validate input"
        ),
        "Service.transform": FunctionInfo(
            name="transform", file_path="app.py", class_name="Service",
            calls=[], description="Transform data"
        ),
        "Service.check_format": FunctionInfo(
            name="check_format", file_path="app.py", class_name="Service",
            calls=[], description="Check format"
        ),
    }
    
    analyzer._analyze_function_chains()
    
    assert len(analyzer.call_chains) >= 1
    # Service.process should be an entry point (has downstream calls, not purely called)
    chain = next((c for c in analyzer.call_chains if c.entry_point == "Service.process"), None)
    assert chain is not None
    assert chain.depth >= 2
    assert "Service.process" in chain.steps


def test_analyze_function_chains_filters_private():
    analyzer = FlowAnalyzer()
    analyzer.functions = {
        "Service.public": FunctionInfo(
            name="public", file_path="app.py", class_name="Service",
            calls=["_private_helper"], description="Public method"
        ),
        "Service._private_helper": FunctionInfo(
            name="_private_helper", file_path="app.py", class_name="Service",
            calls=["do_work"], description="Private helper"
        ),
        "Service.do_work": FunctionInfo(
            name="do_work", file_path="app.py", class_name="Service",
            calls=[], description="Do work"
        ),
    }
    
    analyzer._analyze_function_chains()
    
    # _private_helper should be filtered as entry point (starts with _)
    for chain in analyzer.call_chains:
        assert not chain.entry_point.startswith('_')


def test_generate_call_chain_flowchart():
    analyzer = FlowAnalyzer()
    chain = CallChain(
        entry_point="Service.handle",
        file_path="app.py",
        steps=["Service.handle", "validate", "save"],
        depth=3
    )
    analyzer.call_chains = [chain]
    analyzer.functions = {
        "Service.handle": FunctionInfo(name="handle", file_path="app.py", class_name="Service", calls=["validate", "save"]),
        "validate": FunctionInfo(name="validate", file_path="app.py", calls=[]),
        "save": FunctionInfo(name="save", file_path="app.py", calls=[]),
    }
    
    mermaid = analyzer.generate_call_chain_flowchart(0)
    assert "graph TD" in mermaid
    assert "Service.handle" in mermaid


if __name__ == "__main__":
    test_extract_functions()
    test_extract_api_endpoints_fastapi()
    test_extract_api_endpoints_express()
    test_trace_call_chain()
    test_trace_call_chain_depth_limit()
    test_generate_mermaid_flowchart()
    test_analyze_project_flows_integration()
    test_function_info_pydantic()
    test_api_endpoint_pydantic()
    print("所有 flow_analyzer 测试通过!")
