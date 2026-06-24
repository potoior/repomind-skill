"""渲染器模块 - 生成HTML/Markdown/Mermaid等输出"""

import json
import time
from typing import List, Dict, Optional

from .models import KnowledgeGraph, Entity, EntityType


def render_visjs_html(graph: KnowledgeGraph, repo_name: str) -> str:
    # Prepare entity type counts
    type_counts = {}
    for e in graph.entities:
        type_counts[e.type.value] = type_counts.get(e.type.value, 0) + 1
    
    # Prepare legend items
    legend_items = ""
    type_colors = {
        'Project': '#ff6b6b', 'Module': '#4ecdc4', 'Document': '#45b7d1',
        'Framework': '#96ceb4', 'Database': '#feca57', 'API': '#ff9ff3',
        'Protocol': '#54a0ff', 'Service': '#5f27cd', 'Skill': '#01a3a4',
        'Configuration': '#f368e0', 'Command': '#ff9f43', 'Feature': '#ee5a24',
        'Tool': '#a29bfe'
    }
    for etype, color in type_colors.items():
        if etype in type_counts:
            legend_items += f'<div class="legend-item" data-type="{etype}"><span class="legend-color" style="background:{color}"></span>{etype} ({type_counts[etype]})</div>\n'
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{repo_name} - 知识图谱</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #eee; overflow: hidden; }}
        
        #network {{ width: 100%; height: 100vh; }}
        
        .controls {{
            position: absolute; top: 15px; left: 15px; z-index: 100;
            background: rgba(30, 30, 50, 0.95); border-radius: 12px;
            padding: 20px; width: 280px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .controls h2 {{
            font-size: 18px; margin-bottom: 15px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}
        .controls .stats {{
            display: flex; gap: 15px; margin-bottom: 15px;
            padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;
        }}
        .stats .stat {{ text-align: center; flex: 1; }}
        .stats .stat .num {{ font-size: 24px; font-weight: bold; color: #667eea; }}
        .stats .stat .label {{ font-size: 11px; color: #888; margin-top: 2px; }}
        
        .search-box {{
            width: 100%; padding: 10px 15px; margin-bottom: 15px;
            background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px; color: #eee; font-size: 14px;
            outline: none; transition: all 0.3s;
        }}
        .search-box:focus {{
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102,126,234,0.3);
        }}
        .search-box::placeholder {{ color: #666; }}
        
        .legend {{
            max-height: 200px; overflow-y: auto; margin-bottom: 15px;
            scrollbar-width: thin; scrollbar-color: #444 transparent;
        }}
        .legend-item {{
            display: flex; align-items: center; padding: 6px 10px;
            cursor: pointer; border-radius: 6px; font-size: 13px;
            transition: background 0.2s;
        }}
        .legend-item:hover {{ background: rgba(255,255,255,0.1); }}
        .legend-item.inactive {{ opacity: 0.4; }}
        .legend-color {{
            width: 14px; height: 14px; border-radius: 4px;
            margin-right: 10px; flex-shrink: 0;
        }}
        
        .btn-group {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .btn {{
            padding: 8px 14px; border: none; border-radius: 6px;
            cursor: pointer; font-size: 12px; font-weight: 500;
            transition: all 0.2s;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }}
        .btn-primary:hover {{ transform: translateY(-1px); box-shadow: 0 4px 12px rgba(102,126,234,0.4); }}
        .btn-secondary {{
            background: rgba(255,255,255,0.1); color: #ccc;
        }}
        .btn-secondary:hover {{ background: rgba(255,255,255,0.2); }}
        
        .details {{
            position: absolute; bottom: 15px; right: 15px; z-index: 100;
            background: rgba(30, 30, 50, 0.95); border-radius: 12px;
            padding: 20px; width: 350px; max-height: 400px;
            overflow-y: auto; display: none;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .details.visible {{ display: block; }}
        .details h3 {{
            font-size: 16px; margin-bottom: 12px;
            color: #667eea;
        }}
        .details .detail-row {{
            padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1);
            font-size: 13px;
        }}
        .details .detail-label {{ color: #888; margin-bottom: 4px; }}
        .details .detail-value {{ color: #eee; }}
        .details .close-btn {{
            position: absolute; top: 10px; right: 10px;
            background: none; border: none; color: #888;
            cursor: pointer; font-size: 18px;
        }}
        .details .close-btn:hover {{ color: #eee; }}
        
        .zoom-controls {{
            position: absolute; bottom: 15px; left: 15px; z-index: 100;
            display: flex; flex-direction: column; gap: 5px;
        }}
        .zoom-btn {{
            width: 40px; height: 40px; border-radius: 8px;
            background: rgba(30, 30, 50, 0.95); border: 1px solid rgba(255,255,255,0.2);
            color: #eee; font-size: 18px; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            transition: all 0.2s;
        }}
        .zoom-btn:hover {{ background: rgba(102,126,234,0.5); }}
        
        .tooltip {{
            position: absolute; padding: 8px 12px;
            background: rgba(30, 30, 50, 0.95); border-radius: 6px;
            font-size: 12px; pointer-events: none; z-index: 200;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            display: none;
        }}
    </style>
</head>
<body>
    <div id="network"></div>
    
    <div class="controls">
        <h2>📊 {repo_name}</h2>
        <div class="stats">
            <div class="stat"><div class="num">{len(graph.entities)}</div><div class="label">实体</div></div>
            <div class="stat"><div class="num">{len(graph.relations)}</div><div class="label">关系</div></div>
            <div class="stat"><div class="num">{len(type_counts)}</div><div class="label">类型</div></div>
        </div>
        
        <input type="text" class="search-box" id="searchInput" placeholder="🔍 搜索实体...">
        
        <div class="legend" id="legend">
            {legend_items}
        </div>
        
        <div class="btn-group">
            <button class="btn btn-primary" onclick="resetView()">重置视图</button>
            <button class="btn btn-secondary" onclick="togglePhysics()">物理引擎</button>
            <button class="btn btn-secondary" onclick="exportImage()">导出图片</button>
        </div>
    </div>
    
    <div class="details" id="details">
        <button class="close-btn" onclick="closeDetails()">×</button>
        <h3 id="detailsTitle">实体详情</h3>
        <div id="detailsContent"></div>
    </div>
    
    <div class="zoom-controls">
        <button class="zoom-btn" onclick="zoomIn()">+</button>
        <button class="zoom-btn" onclick="zoomOut()">−</button>
        <button class="zoom-btn" onclick="fitView()">⊡</button>
    </div>
    
    <div class="tooltip" id="tooltip"></div>
    
    <script>
        const entities = {json.dumps([e.model_dump() for e in graph.entities], ensure_ascii=False)};
        const relations = {json.dumps([r.model_dump() for r in graph.relations], ensure_ascii=False)};
        
        const typeColors = {json.dumps(type_colors, ensure_ascii=False)};
        
        const nodes = new vis.DataSet(entities.map((e, i) => ({{
            id: i,
            label: e.name.length > 20 ? e.name.substring(0, 18) + '...' : e.name,
            title: `${{e.type}}: ${{e.name}}`,
            group: e.type,
            font: {{ color: '#fff', size: 14 }},
            borderWidth: 2,
            borderWidthSelected: 4,
            shadow: true
        }})));
        
        const entityMap = {{}};
        entities.forEach((e, i) => entityMap[e.name.toLowerCase()] = i);
        
        const edges = relations.map(r => ({{
            from: entityMap[r.source.toLowerCase()],
            to: entityMap[r.target.toLowerCase()],
            label: r.type,
            arrows: 'to',
            color: {{ color: '#666', highlight: '#667eea', hover: '#888' }},
            font: {{ color: '#888', size: 10, strokeWidth: 3 }},
            smooth: {{ type: 'curvedCW', roundness: 0.2 }}
        }})).filter(e => e.from !== undefined && e.to !== undefined);
        
        const container = document.getElementById('network');
        const data = {{ nodes, edges }};
        const options = {{
            groups: {{
                Project: {{ color: {{ background: '#ff6b6b', border: '#ee5a24' }} }},
                Module: {{ color: {{ background: '#4ecdc4', border: '#0abde3' }} }},
                Document: {{ color: {{ background: '#45b7d1', border: '#2e86de' }} }},
                Framework: {{ color: {{ background: '#96ceb4', border: '#1dd1a1' }} }},
                Database: {{ color: {{ background: '#feca57', border: '#ff9f43' }} }},
                API: {{ color: {{ background: '#ff9ff3', border: '#f368e0' }} }},
                Protocol: {{ color: {{ background: '#54a0ff', border: '#2e86de' }} }},
                Service: {{ color: {{ background: '#5f27cd', border: '#341f97' }} }},
                Skill: {{ color: {{ background: '#01a3a4', border: '#0abde3' }} }},
                Configuration: {{ color: {{ background: '#f368e0', border: '#e056c0' }} }},
                Command: {{ color: {{ background: '#ff9f43', border: '#ee5a24' }} }},
                Feature: {{ color: {{ background: '#ee5a24', border: '#c44569' }} }},
                Tool: {{ color: {{ background: '#a29bfe', border: '#6c5ce7' }} }}
            }},
            physics: {{
                enabled: true,
                solver: 'barnesHut',
                barnesHut: {{
                    gravitationalConstant: -2000,
                    centralGravity: 0.3,
                    springLength: 95,
                    springConstant: 0.04,
                    damping: 0.09
                }},
                stabilization: {{ 
                    enabled: true,
                    iterations: 100,
                    updateInterval: 25
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200,
                zoomView: true,
                dragView: true,
                multiselect: true,
                navigationButtons: false
            }},
            edges: {{
                smooth: {{ type: 'continuous' }}
            }}
        }};
        
        const network = new vis.Network(container, data, options);
        
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', (e) => {{
            const query = e.target.value.toLowerCase();
            if (!query) {{
                nodes.forEach(node => {{
                    nodes.update({{ id: node.id, hidden: false, opacity: 1 }});
                }});
                return;
            }}
            
            nodes.forEach(node => {{
                const entity = entities[node.id];
                const match = entity.name.toLowerCase().includes(query) || 
                              (entity.description && entity.description.toLowerCase().includes(query));
                nodes.update({{ id: node.id, hidden: !match, opacity: match ? 1 : 0.2 }});
            }});
        }});
        
        // Legend filter
        document.querySelectorAll('.legend-item').forEach(item => {{
            item.addEventListener('click', () => {{
                const type = item.dataset.type;
                item.classList.toggle('inactive');
                const isActive = !item.classList.contains('inactive');
                
                nodes.forEach(node => {{
                    const entity = entities[node.id];
                    if (entity.type === type) {{
                        nodes.update({{ id: node.id, hidden: !isActive }});
                    }}
                }});
            }});
        }});
        
        // Node click - show details
        network.on('click', (params) => {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const entity = entities[nodeId];
                showDetails(entity);
                highlightConnected(nodeId);
            }} else {{
                closeDetails();
                resetHighlight();
            }}
        }});
        
        // Hover tooltip
        const tooltip = document.getElementById('tooltip');
        network.on('hoverNode', (params) => {{
            const nodeId = params.node;
            const entity = entities[nodeId];
            tooltip.innerHTML = `<strong>${{entity.name}}</strong><br>${{entity.type}}`;
            tooltip.style.display = 'block';
        }});
        
        network.on('blurNode', () => {{
            tooltip.style.display = 'none';
        }});
        
        container.addEventListener('mousemove', (e) => {{
            tooltip.style.left = (e.clientX + 15) + 'px';
            tooltip.style.top = (e.clientY + 15) + 'px';
        }});
        
        function showDetails(entity) {{
            const details = document.getElementById('details');
            const title = document.getElementById('detailsTitle');
            const content = document.getElementById('detailsContent');
            
            title.textContent = entity.name;
            
            let html = `
                <div class="detail-row">
                    <div class="detail-label">类型</div>
                    <div class="detail-value">${{entity.type}}</div>
                </div>
            `;
            
            if (entity.description) {{
                html += `
                    <div class="detail-row">
                        <div class="detail-label">描述</div>
                        <div class="detail-value">${{entity.description}}</div>
                    </div>
                `;
            }}
            
            if (entity.source_file) {{
                html += `
                    <div class="detail-row">
                        <div class="detail-label">来源</div>
                        <div class="detail-value">${{entity.source_file}}</div>
                    </div>
                `;
            }}
            
            // Find related entities
            const related = [];
            relations.forEach(r => {{
                if (r.source === entity.name) related.push({{ name: r.target, type: r.type, dir: '→' }});
                if (r.target === entity.name) related.push({{ name: r.source, type: r.type, dir: '←' }});
            }});
            
            if (related.length > 0) {{
                html += `<div class="detail-row"><div class="detail-label">关联 (${{related.length}})</div>`;
                related.slice(0, 10).forEach(r => {{
                    html += `<div class="detail-value">${{r.dir}} ${{r.name}} <span style="color:#888">(${{r.type}})</span></div>`;
                }});
                if (related.length > 10) html += `<div class="detail-value" style="color:#888">...还有 ${{related.length - 10}} 个</div>`;
                html += `</div>`;
            }}
            
            content.innerHTML = html;
            details.classList.add('visible');
        }}
        
        function closeDetails() {{
            document.getElementById('details').classList.remove('visible');
        }}
        
        function highlightConnected(nodeId) {{
            const connected = network.getConnectedNodes(nodeId);
            const allNodes = nodes.getIds();
            
            allNodes.forEach(id => {{
                if (id === nodeId || connected.includes(id)) {{
                    nodes.update({{ id, opacity: 1 }});
                }} else {{
                    nodes.update({{ id, opacity: 0.15 }});
                }}
            }});
        }}
        
        function resetHighlight() {{
            nodes.getIds().forEach(id => {{
                nodes.update({{ id, opacity: 1 }});
            }});
        }}
        
        function resetView() {{
            network.fit({{ animation: true }});
            resetHighlight();
            closeDetails();
        }}
        
        let physicsEnabled = true;
        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        }}
        
        function zoomIn() {{
            const scale = network.getScale() * 1.3;
            network.moveTo({{ scale, animation: true }});
        }}
        
        function zoomOut() {{
            const scale = network.getScale() / 1.3;
            network.moveTo({{ scale, animation: true }});
        }}
        
        function fitView() {{
            network.fit({{ animation: true }});
        }}
        
        function exportImage() {{
            const canvas = container.querySelector('canvas');
            const link = document.createElement('a');
            link.download = '{repo_name}_graph.png';
            link.href = canvas.toDataURL();
            link.click();
        }}
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                closeDetails();
                resetHighlight();
            }}
            if (e.key === '/' && document.activeElement !== searchInput) {{
                e.preventDefault();
                searchInput.focus();
            }}
        }});
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


def render_call_chain_mermaid(chain, functions: Dict, standalone: bool = True) -> str:
    entry_id = chain.entry_point.replace('.', '_').replace(' ', '_')

    if standalone:
        mermaid = "graph TD\n"
        mermaid += "    classDef entryNode fill:#4CAF50,stroke:#388E3C,color:white\n"
        mermaid += "    classDef funcNode fill:#2196F3,stroke:#1565C0,color:white\n\n"
    else:
        mermaid = ""

    desc = chain.description or chain.entry_point
    file_info = f"📁 {chain.file_path}"
    mermaid += f"    {entry_id}[\"🚀 {chain.entry_point}\\n{desc}\\n{file_info}\"]:::entryNode\n"

    prev_id = entry_id
    for i, step in enumerate(chain.steps[1:], 1):
        step_id = f"{entry_id}_s{i}"
        step_info = functions.get(step)

        if step_info:
            sdesc = step_info.description or step
            sfile = f"📁 {step_info.file_path}"
            mermaid += f"    {step_id}[\"📦 {step}\\n{sdesc}\\n{sfile}\"]:::funcNode\n"
        else:
            mermaid += f"    {step_id}[\"📦 {step}\"]:::funcNode\n"

        mermaid += f"    {prev_id} --> {step_id}\n"
        prev_id = step_id

    if standalone:
        end_id = f"{entry_id}_end"
        mermaid += f"    end_id[\"✅ 结束\"]:::entryNode\n".replace("end_id", end_id)
        mermaid += f"    {prev_id} --> {end_id}\n"

    return mermaid
