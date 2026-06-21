#!/usr/bin/env python3
"""RepoMind - 智能项目知识图谱生成工具"""

import sys
import os
import io

if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import click
import json
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.text import Text
from rich.columns import Columns
from rich.markdown import Markdown
from rich import box

sys.path.insert(0, str(Path(__file__).parent))

console = Console(force_terminal=True)

from src.repository_loader import RepositoryLoader
from src.knowledge_extractor import KnowledgeExtractor
from src.graph_builder import GraphBuilder
from src.qa_engine import QAEngine
from src.models import EntityType

# ASCII Art Logo
LOGO = """
[bold cyan]
  ____                _           __  __            _ _
 |  _ \ ___  _ __   (_)_ __   |  \/  | ___ _ __ (_) |_ ___  _ __
 | |_) / _ \| '_ \  | | '_ \  | |\/| |/ _ \ '_ \| | __/ _ \| '__|
 |  _ < (_) | |_) | | | | | | | |  | |  __/ | | | | || (_) | |
 |_| \_\___/| .__/  |_|_| |_| |_|  |_|\___|_| |_|_|\__\___/|_|
            |_|
[/bold cyan]
[dim]智能项目知识图谱生成工具 v2.0[/dim]
"""

# 实体类型图标
ENTITY_ICONS = {
    "Module": "📦",
    "Feature": "⚡",
    "Document": "📄",
    "Framework": "🔧",
    "Database": "🗄️",
    "Tool": "🛠️",
    "Protocol": "🔌",
    "Command": "💻",
    "API": "🌐",
    "Project": "📁",
}

# 关系类型图标
RELATION_ICONS = {
    "uses": "→",
    "contains": "⊃",
    "documents": "📝",
    "depends_on": "⟶",
    "extends": "⟶",
    "implements": "⟶",
}


class KnowledgeGraphCLI:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.loader = RepositoryLoader()
        self.extractor = KnowledgeExtractor()
        self.builder = GraphBuilder(str(self.output_dir))
        self.current_graph = None
        self.qa_engine = None
        self.project_name = None

    def analyze(self, path: str, recursive: bool = True) -> dict:
        """分析本地目录或仓库"""
        path = Path(path)
        
        if not path.exists():
            console.print(f"[red]✗ 路径不存在: {path}[/red]")
            return None
        
        # 显示分析开始
        console.print(f"\n[bold]📂 分析项目: [cyan]{path}[/cyan][/bold]\n")
        
        # 扫描文件（带进度条）
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            # 扫描Markdown
            task1 = progress.add_task("[cyan]扫描 Markdown 文件...", total=None)
            md_files = self._find_markdown_files(path, recursive)
            progress.update(task1, completed=100, description=f"[green]✓ 找到 {len(md_files)} 个 Markdown 文件")
            
            # 扫描代码
            task2 = progress.add_task("[cyan]扫描代码文件...", total=None)
            code_files = self._find_code_files(path, recursive)
            progress.update(task2, completed=100, description=f"[green]✓ 找到 {len(code_files)} 个代码文件")
            
            # 加载文档
            task3 = progress.add_task("[cyan]加载文档内容...", total=len(md_files))
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
                    console.print(f"[yellow]⚠ 读取失败 {md_file}: {e}[/yellow]")
                progress.advance(task3)
            
            # 加载代码
            task4 = progress.add_task("[cyan]加载代码内容...", total=len(code_files))
            code_data = []
            for code_file in code_files:
                try:
                    content = self._read_file(code_file)
                    relative_path = str(code_file.relative_to(path))
                    code_data.append((relative_path, content))
                except Exception as e:
                    console.print(f"[yellow]⚠ 读取失败 {code_file}: {e}[/yellow]")
                progress.advance(task4)
            
            # 提取实体和关系
            task5 = progress.add_task("[cyan]提取知识图谱...", total=None)
            entities, relations = self.extractor.extract_from_documents(documents, code_data)
            progress.update(task5, completed=100, description=f"[green]✓ 提取完成")
        
        # 构建图谱
        repo_name = path.name
        self.project_name = repo_name
        graph = self.builder.build_graph(entities, relations, repo_name)
        self.current_graph = graph
        self.qa_engine = QAEngine(graph)
        
        # 生成可视化
        html_path = self.builder.generate_html_visualization(graph, repo_name)
        
        # 显示完成信息
        console.print()
        console.print(Panel(
            f"[bold green]✓ 分析完成![/bold green]\n\n"
            f"  📊 实体: [cyan]{len(entities)}[/cyan] 个\n"
            f"  🔗 关系: [cyan]{len(relations)}[/cyan] 个\n"
            f"  📁 图谱: [dim]{self.output_dir / f'{repo_name}.graph.json'}[/dim]\n"
            f"  🌐 可视化: [dim]{html_path}[/dim]",
            title="[bold]分析结果[/bold]",
            border_style="green"
        ))
        
        return {
            "name": repo_name,
            "entities": len(entities),
            "relations": len(relations),
            "graph_path": str(self.output_dir / f"{repo_name}.graph.json"),
            "html_path": html_path
        }

    def _find_markdown_files(self, path: Path, recursive: bool) -> list:
        """查找Markdown文件"""
        ignore_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build', 'output'}
        
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
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.rb', '.c', '.cpp', '.h'}
        ignore_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build', 'output'}
        
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
        
        # 创建精美的表格
        table = Table(
            title=f"[bold]📊 {self.project_name or '项目'} 分析报告[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("类型", style="cyan", width=15)
        table.add_column("图标", width=4)
        table.add_column("数量", style="green", justify="right", width=8)
        table.add_column("占比", style="yellow", justify="right", width=8)
        
        total = len(graph.entities)
        for type_name, count in sorted(entity_types.items(), key=lambda x: -x[1]):
            icon = ENTITY_ICONS.get(type_name, "•")
            percentage = f"{count/total*100:.1f}%"
            table.add_row(type_name, icon, str(count), percentage)
        
        table.add_section()
        table.add_row("[bold]总计[/bold]", "📊", f"[bold]{total}[/bold]", "100%")
        
        console.print()
        console.print(table)
        
        # 显示模块（带图标）
        modules = [e for e in graph.entities if e.type == EntityType.MODULE]
        if modules:
            console.print()
            tree = Tree("[bold]📦 核心模块[/bold]")
            for m in modules[:15]:
                desc = f" [dim]- {m.description}[/dim]" if m.description else ""
                tree.add(f"[cyan]{m.name}[/cyan]{desc}")
            console.print(tree)
        
        # 显示技术栈（分组显示）
        tech_groups = {
            "🔧 框架": EntityType.FRAMEWORK,
            "🗄️ 数据库": EntityType.DATABASE,
            "🛠️ 工具": EntityType.TOOL,
            "🔌 协议": EntityType.PROTOCOL,
        }
        
        for label, tech_type in tech_groups.items():
            techs = [e for e in graph.entities if e.type == tech_type]
            if techs:
                console.print()
                tree = Tree(f"[bold]{label}[/bold]")
                for t in techs:
                    tree.add(f"[green]{t.name}[/green]")
                console.print(tree)
        
        # 显示关系统计
        relation_types = {}
        for r in graph.relations:
            relation_types[r.type.value] = relation_types.get(r.type.value, 0) + 1
        
        if relation_types:
            console.print()
            rel_table = Table(title="[bold]🔗 关系统计[/bold]", box=box.SIMPLE)
            rel_table.add_column("关系类型", style="cyan")
            rel_table.add_column("数量", style="green", justify="right")
            
            for rel_type, count in sorted(relation_types.items(), key=lambda x: -x[1]):
                icon = RELATION_ICONS.get(rel_type, "→")
                rel_table.add_row(f"{icon} {rel_type}", str(count))
            
            console.print(rel_table)

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
            self.project_name = name
            return True
        except FileNotFoundError:
            return False

    def list_graphs(self) -> list:
        """列出所有已生成的知识图谱"""
        graphs = []
        for f in self.output_dir.glob("*.graph.json"):
            graphs.append(f.stem.replace('.graph', ''))
        return graphs

    def search(self, keyword: str):
        """搜索实体"""
        if not self.current_graph:
            console.print("[red]请先分析一个项目[/red]")
            return
        
        results = []
        keyword_lower = keyword.lower()
        
        for entity in self.current_graph.entities:
            if (keyword_lower in entity.name.lower() or 
                (entity.description and keyword_lower in entity.description.lower())):
                results.append(entity)
        
        if not results:
            console.print(f"[yellow]没有找到包含 '{keyword}' 的实体[/yellow]")
            return
        
        # 显示搜索结果
        table = Table(title=f"[bold]🔍 搜索结果: '{keyword}'[/bold]", box=box.ROUNDED)
        table.add_column("名称", style="cyan")
        table.add_column("类型", style="magenta")
        table.add_column("描述", style="dim")
        table.add_column("来源", style="green")
        
        for entity in results[:20]:
            icon = ENTITY_ICONS.get(entity.type.value, "•")
            table.add_row(
                f"{icon} {entity.name}",
                entity.type.value,
                (entity.description[:30] + "...") if entity.description and len(entity.description) > 30 else (entity.description or "-"),
                entity.source_file or "-"
            )
        
        console.print()
        console.print(table)
        
        if len(results) > 20:
            console.print(f"[dim]... 还有 {len(results) - 20} 个结果[/dim]")

    def show_entity(self, name: str):
        """显示实体详情"""
        if not self.current_graph:
            console.print("[red]请先分析一个项目[/red]")
            return
        
        # 查找实体
        entity = None
        for e in self.current_graph.entities:
            if e.name.lower() == name.lower():
                entity = e
                break
        
        if not entity:
            console.print(f"[red]找不到实体: {name}[/red]")
            return
        
        # 查找相关关系
        relations = []
        for r in self.current_graph.relations:
            if r.source.lower() == name.lower() or r.target.lower() == name.lower():
                relations.append(r)
        
        # 显示详情
        icon = ENTITY_ICONS.get(entity.type.value, "•")
        
        console.print()
        console.print(Panel(
            f"[bold]{icon} {entity.name}[/bold]\n\n"
            f"  类型: [cyan]{entity.type.value}[/cyan]\n"
            f"  描述: [dim]{entity.description or '-'}[/dim]\n"
            f"  来源: [green]{entity.source_file or '-'}[/green]",
            title="[bold]实体详情[/bold]",
            border_style="cyan"
        ))
        
        # 显示相关关系
        if relations:
            rel_table = Table(title="[bold]相关关系[/bold]", box=box.SIMPLE)
            rel_table.add_column("方向", style="cyan", width=8)
            rel_table.add_column("关系", style="magenta", width=12)
            rel_table.add_column("实体", style="green")
            
            for r in relations:
                if r.source.lower() == name.lower():
                    rel_table.add_row("→ 出", r.type.value, r.target)
                else:
                    rel_table.add_row("← 入", r.type.value, r.source)
            
            console.print()
            console.print(rel_table)

    def show_dependencies(self, name: str):
        """显示依赖关系图"""
        if not self.current_graph:
            console.print("[red]请先分析一个项目[/red]")
            return
        
        # 查找实体
        entity = None
        for e in self.current_graph.entities:
            if e.name.lower() == name.lower():
                entity = e
                break
        
        if not entity:
            console.print(f"[red]找不到实体: {name}[/red]")
            return
        
        # 查找依赖
        dependencies = []
        dependents = []
        
        for r in self.current_graph.relations:
            if r.type.value in ['depends_on', 'uses']:
                if r.source.lower() == name.lower():
                    dependencies.append(r.target)
                elif r.target.lower() == name.lower():
                    dependents.append(r.source)
        
        console.print()
        
        # 显示依赖树
        tree = Tree(f"[bold cyan]{name}[/bold cyan] 依赖关系")
        
        if dependencies:
            dep_branch = tree.add("[bold]依赖 →[/bold]")
            for dep in dependencies:
                dep_branch.add(f"[green]{dep}[/green]")
        
        if dependents:
            rev_branch = tree.add("[bold]被依赖 ←[/bold]")
            for dep in dependents:
                rev_branch.add(f"[yellow]{dep}[/yellow]")
        
        if not dependencies and not dependents:
            tree.add("[dim]无依赖关系[/dim]")
        
        console.print(tree)

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
        elif format == 'html':
            self._export_html(output)
        
        console.print(f"[green]✓ 已导出到: {output}[/green]")
        return output

    def _export_csv(self, output: str):
        """导出为CSV"""
        import csv
        
        entities_file = output.replace('.csv', '_entities.csv')
        with open(entities_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'type', 'description', 'source_file'])
            for e in self.current_graph.entities:
                writer.writerow([e.name, e.type.value, e.description or '', e.source_file or ''])
        
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
            f.write(f"# {self.project_name or '项目'} 知识图谱报告\n\n")
            f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 统计概览\n\n")
            f.write(f"| 指标 | 数量 |\n")
            f.write(f"|------|------|\n")
            f.write(f"| 实体 | {len(graph.entities)} |\n")
            f.write(f"| 关系 | {len(graph.relations)} |\n\n")
            
            f.write("## 实体列表\n\n")
            f.write("| 名称 | 类型 | 描述 | 来源 |\n")
            f.write("|------|------|------|------|\n")
            for e in graph.entities:
                f.write(f"| {e.name} | {e.type.value} | {e.description or '-'} | {e.source_file or '-'} |\n")
            
            f.write("\n## 关系列表\n\n")
            f.write("| 源 | 关系 | 目标 |\n")
            f.write("|-----|------|------|\n")
            for r in graph.relations:
                f.write(f"| {r.source} | {r.type.value} | {r.target} |\n")

    def _export_html(self, output: str):
        """导出为HTML报告"""
        graph = self.current_graph
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{self.project_name or '项目'} - 知识图谱报告</title>
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
            <h1>📊 {self.project_name or '项目'} 知识图谱报告</h1>
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
        
        with open(output, 'w', encoding='utf-8') as f:
            f.write(html)


# CLI 命令
@click.group()
@click.option('--output', '-o', default='output', help='输出目录')
@click.pass_context
def cli(ctx, output):
    """[bold cyan]RepoMind[/bold cyan] - 智能项目知识图谱生成工具"""
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
        console.print("\n[bold]💡 下一步操作:[/bold]")
        console.print("  [cyan]python cli.py summary[/cyan]       查看分析摘要")
        console.print("  [cyan]python cli.py query <问题>[/cyan]   查询知识图谱")
        console.print("  [cyan]python cli.py interactive[/cyan]   进入交互模式")


@cli.command()
@click.pass_context
def summary(ctx):
    """显示当前项目的分析摘要"""
    kg = ctx.obj['kg']
    
    graphs = kg.list_graphs()
    if not graphs:
        console.print("[red]没有找到已分析的项目，请先运行 [cyan]analyze[/cyan] 命令[/red]")
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
    
    graphs = kg.list_graphs()
    if not graphs:
        console.print("[red]没有找到已分析的项目，请先运行 [cyan]analyze[/cyan] 命令[/red]")
        return
    
    if kg.load_graph(graphs[0]):
        answer = kg.query(question)
        console.print()
        console.print(Panel(
            answer,
            title="[bold]💬 回答[/bold]",
            border_style="green",
            padding=(1, 2)
        ))
    else:
        console.print("[red]加载知识图谱失败[/red]")


@cli.command()
@click.argument('keyword')
@click.pass_context
def search(ctx, keyword):
    """搜索实体"""
    kg = ctx.obj['kg']
    
    graphs = kg.list_graphs()
    if not graphs:
        console.print("[red]没有找到已分析的项目[/red]")
        return
    
    if kg.load_graph(graphs[0]):
        kg.search(keyword)


@cli.command()
@click.argument('name')
@click.pass_context
def entity(ctx, name):
    """查看实体详情"""
    kg = ctx.obj['kg']
    
    graphs = kg.list_graphs()
    if not graphs:
        console.print("[red]没有找到已分析的项目[/red]")
        return
    
    if kg.load_graph(graphs[0]):
        kg.show_entity(name)


@cli.command()
@click.argument('name')
@click.pass_context
def deps(ctx, name):
    """查看依赖关系"""
    kg = ctx.obj['kg']
    
    graphs = kg.list_graphs()
    if not graphs:
        console.print("[red]没有找到已分析的项目[/red]")
        return
    
    if kg.load_graph(graphs[0]):
        kg.show_dependencies(name)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'markdown', 'html']), default='json', help='导出格式')
@click.option('--output', '-o', help='输出文件路径')
@click.pass_context
def export(ctx, format, output):
    """导出知识图谱"""
    kg = ctx.obj['kg']
    
    graphs = kg.list_graphs()
    if not graphs:
        console.print("[red]没有找到已分析的项目[/red]")
        return
    
    if kg.load_graph(graphs[0]):
        kg.export(format, output)


@cli.command(name='list')
@click.pass_context
def list_graphs(ctx):
    """列出所有已生成的知识图谱"""
    kg = ctx.obj['kg']
    graphs = kg.list_graphs()
    
    if not graphs:
        console.print("[yellow]没有找到已分析的项目[/yellow]")
        return
    
    table = Table(
        title="[bold]📁 已分析的项目[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("项目名称", style="cyan")
    table.add_column("操作", style="green")
    
    for i, name in enumerate(graphs, 1):
        table.add_row(str(i), name, f"python cli.py load {name}")
    
    console.print()
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
    
    graphs = kg.list_graphs()
    if not graphs:
        console.print("[red]没有找到已分析的项目，请先运行 [cyan]analyze[/cyan] 命令[/red]")
        return
    
    if not kg.load_graph(graphs[0]):
        console.print("[red]加载知识图谱失败[/red]")
        return
    
    console.print()
    console.print(Panel(
        "[bold]🔮 交互式查询模式[/bold]\n\n"
        "  [cyan]模块[/cyan] / [cyan]技术栈[/cyan] / [cyan]数据库[/cyan]  查看分类\n"
        "  [cyan]<名称>是什么[/cyan]                查看实体详情\n"
        "  [cyan]<名称>依赖什么[/cyan]              查看依赖关系\n"
        "  [cyan]search <关键词>[/cyan]              搜索实体\n"
        "  [cyan]summary[/cyan]                      查看摘要\n"
        "  [cyan]help[/cyan]                         显示帮助\n"
        "  [cyan]quit[/cyan]                         退出",
        title="[bold]使用说明[/bold]",
        border_style="cyan"
    ))
    
    while True:
        try:
            question = console.input("\n[bold cyan]❯ [/bold cyan]")
            
            if not question.strip():
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                console.print("[yellow]👋 再见![/yellow]")
                break
            
            if question.lower() == 'summary':
                kg.show_summary()
                continue
            
            if question.lower() == 'help':
                console.print(Panel(
                    "可用查询:\n"
                    "- [cyan]模块[/cyan]: 查看所有模块\n"
                    "- [cyan]技术栈[/cyan]: 查看技术栈\n"
                    "- [cyan]数据库[/cyan]: 查看数据库\n"
                    "- [cyan]工具[/cyan]: 查看工具\n"
                    "- [cyan]<实体名>是什么[/cyan]: 查看实体详情\n"
                    "- [cyan]<实体名>依赖什么[/cyan]: 查看依赖关系\n"
                    "- [cyan]search <关键词>[/cyan]: 搜索实体",
                    border_style="yellow"
                ))
                continue
            
            if question.lower().startswith('search '):
                keyword = question[7:].strip()
                kg.search(keyword)
                continue
            
            answer = kg.query(question)
            console.print()
            console.print(Panel(
                answer,
                border_style="green",
                padding=(1, 2)
            ))
        
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 再见![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]✗ 错误: {e}[/red]")


@cli.command()
def version():
    """显示版本信息"""
    console.print()
    console.print(Panel(
        "[bold cyan]RepoMind[/bold cyan] - 智能项目知识图谱生成工具\n\n"
        "  版本: [green]2.0.0[/green]\n"
        "  作者: [dim]RepoMind Team[/dim]\n"
        "  仓库: [blue]https://github.com/potoior/repomind-skill[/blue]",
        title="[bold]版本信息[/bold]",
        border_style="cyan"
    ))


@cli.command()
def logo():
    """显示Logo"""
    console.print(LOGO)


if __name__ == '__main__':
    cli()