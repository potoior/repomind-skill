"""渲染器模块 - 生成HTML/Markdown/Mermaid等输出"""

import json
import time
from typing import List, Dict, Optional

from .models import KnowledgeGraph, Entity, EntityType


def render_visjs_html(graph: KnowledgeGraph, repo_name: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{repo_name} - 知识图谱</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #network {{ width: 100%; height: 100vh; }}
        .info {{ position: absolute; top: 10px; left: 10px; background: white; padding: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
    </style>
</head>
<body>
    <div class="info">
        <h2>{repo_name}</h2>
        <p>实体: {len(graph.entities)} | 关系: {len(graph.relations)}</p>
    </div>
    <div id="network"></div>
    <script>
        const entities = {json.dumps([e.model_dump() for e in graph.entities], ensure_ascii=False)};
        const relations = {json.dumps([r.model_dump() for r in graph.relations], ensure_ascii=False)};

        const nodes = new vis.DataSet(entities.map((e, i) => ({{
            id: i,
            label: e.name,
            title: `${{e.type}}: ${{e.name}}`,
            group: e.type
        }})));

        const entityMap = {{}};
        entities.forEach((e, i) => entityMap[e.name.toLowerCase()] = i);

        const edges = relations.map(r => ({{
            from: entityMap[r.source.toLowerCase()] || 0,
            to: entityMap[r.target.toLowerCase()] || 0,
            label: r.type,
            arrows: 'to'
        }})).filter(e => e.from !== undefined && e.to !== undefined);

        const container = document.getElementById('network');
        const data = {{ nodes, edges }};
        const options = {{
            groups: {{
                Project: {{ color: '#ff6b6b' }},
                Module: {{ color: '#4ecdc4' }},
                Document: {{ color: '#45b7d1' }},
                Framework: {{ color: '#96ceb4' }},
                Database: {{ color: '#feca57' }},
                API: {{ color: '#ff9ff3' }},
                Protocol: {{ color: '#54a0ff' }},
                Service: {{ color: '#5f27cd' }},
                Skill: {{ color: '#01a3a4' }},
                Configuration: {{ color: '#f368e0' }},
                Command: {{ color: '#ff9f43' }},
                Feature: {{ color: '#ee5a24' }}
            }},
            physics: {{ stabilization: false }}
        }};

        new vis.Network(container, data, options);
    </script>
</body>
</html>"""


def render_report_html(graph: KnowledgeGraph, project_name: str) -> str:
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{project_name} - 知识图谱报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
        .stat-card .number {{ font-size: 36px; font-weight: bold; color: #667eea; }}
        .stat-card .label {{ color: #666; margin-top: 5px; }}
        .section {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .section h2 {{ color: #333; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #667eea; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; font-weight: 600; color: #333; }}
        tr:hover {{ background: #f5f5f5; }}
        .type-badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }}
        .type-Module {{ background: #e3f2fd; color: #1976d2; }}
        .type-Feature {{ background: #f3e5f5; color: #7b1fa2; }}
        .type-Document {{ background: #e8f5e9; color: #388e3c; }}
        .type-Framework {{ background: #fff3e0; color: #f57c00; }}
        .type-Database {{ background: #fce4ec; color: #c62828; }}
        .type-Tool {{ background: #e0f2f1; color: #00695c; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {project_name} 知识图谱报告</h1>
            <p>生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="number">{len(graph.entities)}</div>
                <div class="label">实体总数</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(graph.relations)}</div>
                <div class="label">关系总数</div>
            </div>
            <div class="stat-card">
                <div class="number">{len([e for e in graph.entities if e.type.value == 'Module'])}</div>
                <div class="label">模块数量</div>
            </div>
            <div class="stat-card">
                <div class="number">{len([e for e in graph.entities if e.type.value == 'Document'])}</div>
                <div class="label">文档数量</div>
            </div>
        </div>
        
        <div class="section">
            <h2>实体列表</h2>
            <table>
                <tr><th>名称</th><th>类型</th><th>描述</th><th>来源</th></tr>
"""

    for e in graph.entities:
        html += f"""                <tr>
                    <td>{e.name}</td>
                    <td><span class="type-badge type-{e.type.value}">{e.type.value}</span></td>
                    <td>{e.description or '-'}</td>
                    <td>{e.source_file or '-'}</td>
                </tr>
"""

    html += """            </table>
        </div>
        
        <div class="section">
            <h2>关系列表</h2>
            <table>
                <tr><th>源</th><th>关系</th><th>目标</th></tr>
"""

    for r in graph.relations:
        html += f"""                <tr>
                    <td>{r.source}</td>
                    <td>{r.type.value}</td>
                    <td>{r.target}</td>
                </tr>
"""

    html += """            </table>
        </div>
    </div>
</body>
</html>"""

    return html


def render_report_markdown(graph: KnowledgeGraph, project_name: str) -> str:
    lines = []
    lines.append(f"# {project_name} 知识图谱报告\n")
    lines.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append("## 统计概览\n")
    lines.append("| 指标 | 数量 |")
    lines.append("|------|------|")
    lines.append(f"| 实体 | {len(graph.entities)} |")
    lines.append(f"| 关系 | {len(graph.relations)} |\n")
    lines.append("## 实体列表\n")
    lines.append("| 名称 | 类型 | 描述 | 来源 |")
    lines.append("|------|------|------|------|")
    for e in graph.entities:
        lines.append(f"| {e.name} | {e.type.value} | {e.description or '-'} | {e.source_file or '-'} |")
    lines.append("\n## 关系列表\n")
    lines.append("| 源 | 关系 | 目标 |")
    lines.append("|-----|------|------|")
    for r in graph.relations:
        lines.append(f"| {r.source} | {r.type.value} | {r.target} |")
    return "\n".join(lines) + "\n"


def render_mermaid_flowchart(endpoints, functions: Dict, endpoint_idx: int = None) -> str:
    if endpoint_idx is not None and 0 <= endpoint_idx < len(endpoints):
        selected = [endpoints[endpoint_idx]]
    else:
        selected = endpoints

    if not selected:
        return "graph TD\n    A[No API endpoints found]"

    mermaid = "graph TD\n"
    mermaid += "    %% 样式定义\n"
    mermaid += "    classDef apiNode fill:#4CAF50,stroke:#388E3C,color:white\n"
    mermaid += "    classDef funcNode fill:#2196F3,stroke:#1565C0,color:white\n"
    mermaid += "    classDef dbNode fill:#FF9800,stroke:#EF6C00,color:white\n\n"

    for endpoint in selected:
        api_id = f"API_{endpoint.method}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}"
        api_label = f"{endpoint.method} {endpoint.path}"
        mermaid += f"    {api_id}[\"🌐 {api_label}\"]:::apiNode\n"

        prev_id = api_id
        for i, step in enumerate(endpoint.steps):
            step_id = f"{api_id}_step{i}"
            step_info = functions.get(step)

            if step_info:
                desc = step_info.description or step
                file_info = f"📁 {step_info.file_path}"
                mermaid += f"    {step_id}[\"📦 {step}\\n{desc}\\n{file_info}\"]:::funcNode\n"
            else:
                mermaid += f"    {step_id}[\"📦 {step}\"]:::funcNode\n"

            mermaid += f"    {prev_id} --> {step_id}\n"
            prev_id = step_id

        end_id = f"{api_id}_end"
        mermaid += f"    {end_id}[\"✅ 返回响应\"]:::apiNode\n"
        mermaid += f"    {prev_id} --> {end_id}\n\n"

    return mermaid
