import json
from pathlib import Path
from typing import List
from .models import Entity, Relation, KnowledgeGraph
from .renderers import render_visjs_html


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
        html_content = render_visjs_html(graph, repo_name)

        output_file = self.output_dir / f"{repo_name}.graph.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"可视化已保存到: {output_file}")
        return str(output_file)