import json
from pathlib import Path
from typing import List
from .models import Entity, Relation, KnowledgeGraph


class GraphBuilder:
    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def build_graph(self, entities: List[Entity], relations: List[Relation], repo_name: str) -> KnowledgeGraph:
        graph = KnowledgeGraph(
            entities=entities,
            relations=relations
        )

        output_file = self.output_dir / f"{repo_name}.graph.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(graph.model_dump(), f, ensure_ascii=False, indent=2)

        print(f"知识图谱已保存到: {output_file}")
        print(f"实体数量: {len(entities)}")
        print(f"关系数量: {len(relations)}")

        return graph

    def load_graph(self, repo_name: str) -> KnowledgeGraph:
        input_file = self.output_dir / f"{repo_name}.graph.json"

        if not input_file.exists():
            raise FileNotFoundError(f"找不到知识图谱文件: {input_file}")

        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return KnowledgeGraph(**data)

    def generate_html_visualization(self, graph: KnowledgeGraph, repo_name: str) -> str:
        html_content = f"""<!DOCTYPE html>
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

        output_file = self.output_dir / f"{repo_name}.graph.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"可视化已保存到: {output_file}")
        return str(output_file)