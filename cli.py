#!/usr/bin/env python3
"""GitHub Knowledge Graph CLI - 项目知识图谱生成工具"""

import sys
import os
import io

if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import click
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel

sys.path.insert(0, str(Path(__file__).parent))

console = Console(force_terminal=True)

from src.repository_loader import RepositoryLoader
from src.knowledge_extractor import KnowledgeExtractor
from src.graph_builder import GraphBuilder
from src.qa_engine import QAEngine
from src.models import EntityType


class KnowledgeGraphCLI:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.loader = RepositoryLoader()
        self.extractor = KnowledgeExtractor()
        self.builder = GraphBuilder(str(self.output_dir))
        self.current_graph = None
        self.qa_engine = None

    def analyze(self, path: str, recursive: bool = True) -> dict:
        """分析本地目录或仓库"""
        path = Path(path)
        
        if not path.exists():
            console.print(f"[red]错误: 路径不存在: {path}[/red]")
            return None
        
        console.print(f"\n[bold blue]开始分析: {path}[/bold blue]\n")
        
        # 扫描文件
        md_files = self._find_markdown_files(path, recursive)
        code_files = self._find_code_files(path, recursive)
        
        console.print(f"找到 [green]{len(md_files)}[/green] 个 Markdown 文件")
        console.print(f"找到 [green]{len(code_files)}[/green] 个代码文件\n")
        
        # 加载文档
        documents = []
        for md_file in md_files:
            try:
                content = self._read_file(md_file)
                relative_path = md_file.relative_to(path)
                title = self._extract_title(content)
                headings = self._extract_headings(content)
                
                from src.models import Document
                documents.append(Document(
                    path=str(relative_path),
                    title=title,
                    content=content,
                    headings=headings
                ))
            except Exception as e:
                console.print(f"[yellow]警告: 读取失败 {md_file}: {e}[/yellow]")
        
        # 加载代码
        code_data = []
        for code_file in code_files:
            try:
                content = self._read_file(code_file)
                relative_path = str(code_file.relative_to(path))
                code_data.append((relative_path, content))
            except Exception as e:
                console.print(f"[yellow]警告: 读取失败 {code_file}: {e}[/yellow]")
        
        # 提取实体和关系
        with console.status("[bold green]提取知识图谱..."):
            entities, relations = self.extractor.extract_from_documents(documents, code_data)
        
        console.print(f"\n提取了 [cyan]{len(entities)}[/cyan] 个实体和 [cyan]{len(relations)}[/cyan] 个关系")
        
        # 构建图谱
        repo_name = path.name
        graph = self.builder.build_graph(entities, relations, repo_name)
        self.current_graph = graph
        self.qa_engine = QAEngine(graph)
        
        # 生成可视化
        html_path = self.builder.generate_html_visualization(graph, repo_name)
        
        console.print(f"\n[bold green]✓ 分析完成![/bold green]")
        console.print(f"  知识图谱: {self.output_dir / f'{repo_name}.graph.json'}")
        console.print(f"  可视化: {html_path}")
        
        return {
            "name": repo_name,
            "entities": len(entities),
            "relations": len(relations),
            "graph_path": str(self.output_dir / f"{repo_name}.graph.json"),
            "html_path": html_path
        }

    def _find_markdown_files(self, path: Path, recursive: bool) -> list:
        """查找Markdown文件"""
        ignore_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build'}
        
        if recursive:
            files = []
            for root, dirs, filenames in os.walk(path):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                for f in filenames:
                    if f.endswith('.md'):
                        files.append(Path(root) / f)
            return files
        else:
            return list(path.glob("*.md"))

    def _find_code_files(self, path: Path, recursive: bool) -> list:
        """查找代码文件"""
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.rb'}
        ignore_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build'}
        
        files = []
        if recursive:
            for root, dirs, filenames in os.walk(path):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                for f in filenames:
                    if Path(f).suffix in extensions:
                        files.append(Path(root) / f)
        else:
            for ext in extensions:
                files.extend(path.glob(f"*{ext}"))
        
        return files

    def _read_file(self, file_path: Path) -> str:
        """读取文件，支持多种编码"""
        encodings = ['utf-8', 'utf-8-sig', 'utf-16', 'latin-1', 'gbk']
        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError(f"无法读取文件: {file_path}")

    def _extract_title(self, content: str) -> str:
        """提取标题"""
        for line in content.split('\n'):
            if line.startswith('# '):
                return line[2:].strip()
        return "Untitled"

    def _extract_headings(self, content: str) -> list:
        """提取标题列表"""
        return [line.strip() for line in content.split('\n') if line.startswith('#')]

    def show_summary(self):
        """显示摘要"""
        if not self.current_graph:
            console.print("[red]请先分析一个项目[/red]")
            return
        
        graph = self.current_graph
        
        # 统计
        entity_types = {}
        for e in graph.entities:
            entity_types[e.type.value] = entity_types.get(e.type.value, 0) + 1
        
        # 创建表格
        table = Table(title="项目分析报告")
        table.add_column("类型", style="cyan")
        table.add_column("数量", style="green", justify="right")
        
        for type_name, count in sorted(entity_types.items(), key=lambda x: -x[1]):
            table.add_row(type_name, str(count))
        
        table.add_section()
        table.add_row("总计", str(len(graph.entities)))
        
        console.print(table)
        
        # 显示模块
        modules = [e for e in graph.entities if e.type == EntityType.MODULE]
        if modules:
            tree = Tree("\n[bold]核心模块[/bold]")
            for m in modules[:15]:
                tree.add(f"[cyan]{m.name}[/cyan]" + (f" - {m.description}" if m.description else ""))
            console.print(tree)
        
        # 显示技术栈
        tech_types = [EntityType.FRAMEWORK, EntityType.DATABASE, EntityType.TOOL, EntityType.PROTOCOL]
        for tech_type in tech_types:
            techs = [e for e in graph.entities if e.type == tech_type]
            if techs:
                tree = Tree(f"\n[bold]{tech_type.value}[/bold]")
                for t in techs:
                    tree.add(f"[green]{t.name}[/green]")
                console.print(tree)

    def query(self, question: str) -> str:
        """查询知识图谱"""
        if not self.qa_engine:
            return "请先分析一个项目"
        return self.qa_engine.answer_question(question)

    def load_graph(self, name: str) -> bool:
        """加载已有的知识图谱"""
        try:
            graph = self.builder.load_graph(name)
            self.current_graph = graph
            self.qa_engine = QAEngine(graph)
            return True
        except FileNotFoundError:
            return False

    def list_graphs(self) -> list:
        """列出所有已生成的知识图谱"""
        graphs = []
        for f in self.output_dir.glob("*.graph.json"):
            graphs.append(f.stem.replace('.graph', ''))
        return graphs

    def export(self, format: str = 'json', output: str = None) -> str:
        """导出知识图谱"""
        if not self.current_graph:
            console.print("[red]请先分析一个项目[/red]")
            return None
        
        if not output:
            output = f"knowledge_graph.{format}"
        
        if format == 'json':
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(self.current_graph.model_dump(), f, ensure_ascii=False, indent=2)
        elif format == 'csv':
            self._export_csv(output)
        elif format == 'markdown':
            self._export_markdown(output)
        
        console.print(f"[green]✓ 已导出到: {output}[/green]")
        return output

    def _export_csv(self, output: str):
        """导出为CSV"""
        import csv
        
        # 导出实体
        entities_file = output.replace('.csv', '_entities.csv')
        with open(entities_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'type', 'description', 'source_file'])
            for e in self.current_graph.entities:
                writer.writerow([e.name, e.type.value, e.description or '', e.source_file or ''])
        
        # 导出关系
        relations_file = output.replace('.csv', '_relations.csv')
        with open(relations_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['source', 'target', 'type', 'source_file'])
            for r in self.current_graph.relations:
                writer.writerow([r.source, r.target, r.type.value, r.source_file or ''])

    def _export_markdown(self, output: str):
        """导出为Markdown"""
        graph = self.current_graph
        
        with open(output, 'w', encoding='utf-8') as f:
            f.write("# 知识图谱报告\n\n")
            
            f.write("## 统计概览\n\n")
            f.write(f"- 实体数量: {len(graph.entities)}\n")
            f.write(f"- 关系数量: {len(graph.relations)}\n\n")
            
            f.write("## 实体列表\n\n")
            f.write("| 名称 | 类型 | 描述 | 来源 |\n")
            f.write("|------|------|------|------|\n")
            for e in graph.entities:
                f.write(f"| {e.name} | {e.type.value} | {e.description or '-'} | {e.source_file or '-'} |\n")
            
            f.write("\n## 关系列表\n\n")
            f.write("| 源 | 目标 | 类型 |\n")
            f.write("|-----|------|------|\n")
            for r in graph.relations:
                f.write(f"| {r.source} | {r.target} | {r.type.value} |\n")


# CLI 命令
@click.group()
@click.option('--output', '-o', default='output', help='输出目录')
@click.pass_context
def cli(ctx, output):
    """GitHub Knowledge Graph CLI - 项目知识图谱生成工具"""
    ctx.ensure_object(dict)
    ctx.obj['kg'] = KnowledgeGraphCLI(output)


@cli.command()
@click.argument('path')
@click.option('--no-recursive', is_flag=True, help='不递归扫描子目录')
@click.pass_context
def analyze(ctx, path, no_recursive):
    """分析本地目录，生成知识图谱"""
    kg = ctx.obj['kg']
    result = kg.analyze(path, recursive=not no_recursive)
    
    if result:
        console.print("\n[bold]使用以下命令查看更多信息:[/bold]")
        console.print(f"  python cli.py summary")
        console.print(f"  python cli.py query <问题>")


@cli.command()
@click.pass_context
def summary(ctx):
    """显示当前项目的分析摘要"""
    kg = ctx.obj['kg']
    
    # 尝试加载最新的图谱
    graphs = kg.list_graphs()
    if not graphs:
        console.print("[red]没有找到已分析的项目，请先运行 analyze 命令[/red]")
        return
    
    if kg.load_graph(graphs[0]):
        kg.show_summary()
    else:
        console.print("[red]加载知识图谱失败[/red]")


@cli.command()
@click.argument('question')
@click.pass_context
def query(ctx, question):
    """查询知识图谱"""
    kg = ctx.obj['kg']
    
    # 尝试加载最新的图谱
    graphs = kg.list_graphs()
    if not graphs:
        console.print("[red]没有找到已分析的项目，请先运行 analyze 命令[/red]")
        return
    
    if kg.load_graph(graphs[0]):
        answer = kg.query(question)
        console.print(Panel(answer, title="回答", border_style="green"))
    else:
        console.print("[red]加载知识图谱失败[/red]")


@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'markdown']), default='json', help='导出格式')
@click.option('--output', '-o', help='输出文件路径')
@click.pass_context
def export(ctx, format, output):
    """导出知识图谱"""
    kg = ctx.obj['kg']
    
    # 尝试加载最新的图谱
    graphs = kg.list_graphs()
    if not graphs:
        console.print("[red]没有找到已分析的项目，请先运行 analyze 命令[/red]")
        return
    
    if kg.load_graph(graphs[0]):
        kg.export(format, output)
    else:
        console.print("[red]加载知识图谱失败[/red]")


@cli.command()
@click.pass_context
def list(ctx):
    """列出所有已生成的知识图谱"""
    kg = ctx.obj['kg']
    graphs = kg.list_graphs()
    
    if not graphs:
        console.print("[yellow]没有找到已分析的项目[/yellow]")
        return
    
    table = Table(title="已分析的项目")
    table.add_column("项目名称", style="cyan")
    
    for name in graphs:
        table.add_row(name)
    
    console.print(table)


@cli.command()
@click.argument('name')
@click.pass_context
def load(ctx, name):
    """加载指定的知识图谱"""
    kg = ctx.obj['kg']
    
    if kg.load_graph(name):
        console.print(f"[green]✓ 已加载: {name}[/green]")
        kg.show_summary()
    else:
        console.print(f"[red]找不到项目: {name}[/red]")


@cli.command()
@click.pass_context
def interactive(ctx):
    """进入交互式查询模式"""
    kg = ctx.obj['kg']
    
    # 尝试加载最新的图谱
    graphs = kg.list_graphs()
    if not graphs:
        console.print("[red]没有找到已分析的项目，请先运行 analyze 命令[/red]")
        return
    
    if not kg.load_graph(graphs[0]):
        console.print("[red]加载知识图谱失败[/red]")
        return
    
    console.print(Panel(
        "[bold]交互式查询模式[/bold]\n\n"
        "输入问题进行查询，输入 'quit' 或 'exit' 退出\n"
        "输入 'summary' 查看摘要\n"
        "输入 'help' 查看帮助",
        border_style="blue"
    ))
    
    while True:
        try:
            question = console.input("\n[bold cyan]> [/bold cyan]")
            
            if not question.strip():
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                console.print("[yellow]再见![/yellow]")
                break
            
            if question.lower() == 'summary':
                kg.show_summary()
                continue
            
            if question.lower() == 'help':
                console.print(Panel(
                    "可用查询:\n"
                    "- 模块: 查看所有模块\n"
                    "- 技术栈: 查看技术栈\n"
                    "- 数据库: 查看数据库\n"
                    "- 工具: 查看工具\n"
                    "- <实体名>是什么: 查看实体详情\n"
                    "- <实体名>依赖什么: 查看依赖关系",
                    border_style="yellow"
                ))
                continue
            
            answer = kg.query(question)
            console.print(Panel(answer, border_style="green"))
        
        except KeyboardInterrupt:
            console.print("\n[yellow]再见![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")


if __name__ == '__main__':
    cli()