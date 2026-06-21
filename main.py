#!/usr/bin/env python3
import sys
import json
import io
import os
from pathlib import Path

if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from src.repository_loader import RepositoryLoader
from src.knowledge_extractor import KnowledgeExtractor
from src.graph_builder import GraphBuilder
from src.qa_engine import QAEngine


class GitHubKnowledgeGraph:
    def __init__(self):
        self.repo_loader = RepositoryLoader()
        self.extractor = KnowledgeExtractor()
        self.graph_builder = GraphBuilder()
        self.current_graph = None
        self.qa_engine = None

    def analyze_repo(self, repo_url: str):
        print(f"开始分析仓库: {repo_url}")

        context = self.repo_loader.clone_repo(repo_url)
        print(f"仓库名称: {context.repo_name}")

        documents = self.repo_loader.load_documents(context)
        print(f"加载了 {len(documents)} 个文档")

        code_files = self.repo_loader.load_code_files(context)
        print(f"加载了 {len(code_files)} 个代码文件")

        entities, relations = self.extractor.extract_from_documents(documents, code_files)
        print(f"提取了 {len(entities)} 个实体和 {len(relations)} 个关系")

        self.current_graph = self.graph_builder.build_graph(entities, relations, context.repo_name)
        self.qa_engine = QAEngine(self.current_graph)

        self.graph_builder.generate_html_visualization(self.current_graph, context.repo_name)

        print("\n分析完成!")
        self._print_summary()

    def _print_summary(self):
        if not self.current_graph:
            return

        print("\n" + "=" * 50)
        print("项目分析报告")
        print("=" * 50)

        entity_types = {}
        for e in self.current_graph.entities:
            entity_types[e.type.value] = entity_types.get(e.type.value, 0) + 1

        print(f"\n【统计概览】")
        print(f"  实体总数: {len(self.current_graph.entities)}")
        print(f"  关系总数: {len(self.current_graph.relations)}")
        print(f"  实体类型分布:")
        for type_name, count in sorted(entity_types.items(), key=lambda x: -x[1]):
            print(f"    - {type_name}: {count}")

        documents = [e for e in self.current_graph.entities if e.type.value == "Document"]
        if documents:
            print(f"\n【文档列表】")
            for d in documents:
                print(f"  - {d.name} ({d.source_file})")

        modules = [e for e in self.current_graph.entities if e.type.value == "Module"]
        if modules:
            print(f"\n【核心模块】")
            for m in modules[:10]:
                print(f"  - {m.name}")

        frameworks = [e for e in self.current_graph.entities if e.type.value == "Framework"]
        if frameworks:
            print(f"\n【技术栈 - Framework】")
            for f in frameworks:
                print(f"  - {f.name}")

        databases = [e for e in self.current_graph.entities if e.type.value == "Database"]
        if databases:
            print(f"\n【技术栈 - Database】")
            for d in databases:
                print(f"  - {d.name}")

        tools = [e for e in self.current_graph.entities if e.type.value == "Tool"]
        if tools:
            print(f"\n【技术栈 - Tool】")
            for t in tools:
                print(f"  - {t.name}")

        protocols = [e for e in self.current_graph.entities if e.type.value == "Protocol"]
        if protocols:
            print(f"\n【技术栈 - Protocol】")
            for p in protocols:
                print(f"  - {p.name}")

        relation_types = {}
        for r in self.current_graph.relations:
            relation_types[r.type.value] = relation_types.get(r.type.value, 0) + 1

        print(f"\n【关系类型分布】")
        for type_name, count in sorted(relation_types.items(), key=lambda x: -x[1]):
            print(f"  - {type_name}: {count}")

        print("\n" + "=" * 50)

    def query(self, question: str) -> str:
        if not self.qa_engine:
            return "请先分析一个仓库。使用: analyze <repo_url>"
        return self.qa_engine.answer_question(question)

    def show_graph(self):
        if not self.current_graph:
            print("请先分析一个仓库。")
            return

        print("\n=== 知识图谱 ===")
        print(f"实体数量: {len(self.current_graph.entities)}")
        print(f"关系数量: {len(self.current_graph.relations)}")

        print("\n实体列表:")
        for entity in self.current_graph.entities[:30]:
            print(f"  [{entity.type.value}] {entity.name}")

        print("\n关系列表:")
        for relation in self.current_graph.relations[:30]:
            print(f"  {relation.source} --[{relation.type.value}]--> {relation.target}")

    def export_graph(self, filename: str = None):
        if not self.current_graph:
            print("请先分析一个仓库。")
            return

        if not filename:
            filename = "knowledge_graph.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.current_graph.model_dump(), f, ensure_ascii=False, indent=2)

        print(f"知识图谱已导出到: {filename}")


def main():
    kg = GitHubKnowledgeGraph()

    print("GitHub Knowledge Graph Skill")
    print("=" * 40)
    print("Commands:")
    print("  analyze <repo_url> - Analyze GitHub repository")
    print("  query <question>   - Query knowledge graph")
    print("  show               - Show graph summary")
    print("  export [filename]  - Export graph JSON")
    print("  quit               - Exit program")
    print("=" * 40)

    if not sys.stdin.isatty():
        for line in sys.stdin:
            user_input = line.strip()
            if not user_input:
                continue
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            if command == "analyze":
                if not args:
                    print("Usage: analyze <repo_url>")
                    continue
                kg.analyze_repo(args)
            elif command == "query":
                if not args:
                    print("Usage: query <question>")
                    continue
                answer = kg.query(args)
                print(f"\n{answer}")
            elif command == "show":
                kg.show_graph()
            elif command == "export":
                kg.export_graph(args if args else None)
            else:
                print(f"Unknown command: {command}")
        return

    while True:
        try:
            user_input = input("\n> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            if command == "analyze":
                if not args:
                    print("Usage: analyze <repo_url>")
                    continue
                kg.analyze_repo(args)

            elif command == "query":
                if not args:
                    print("Usage: query <question>")
                    continue
                answer = kg.query(args)
                print(f"\n{answer}")

            elif command == "show":
                kg.show_graph()

            elif command == "export":
                kg.export_graph(args if args else None)

            else:
                print(f"Unknown command: {command}")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()