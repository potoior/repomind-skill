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

DAEMON_PORT = 19832


def _try_daemon(command: str, args: dict = None):
    from src.client import is_daemon_running, request
    if not is_daemon_running(port=DAEMON_PORT):
        return None
    resp = request(command, args or {}, port=DAEMON_PORT)
    if "error" in resp:
        console.print(f"[red]✗ {resp['error']}[/red]")
        return "error"
    return resp.get("result")


class KnowledgeGraphCLI:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._loader = None
        self._extractor = None
        self._builder = None
        self.current_graph = None
        self.qa_engine = None
        self.project_name = None
        self.flow_analyzer = None
        self.current_path = None

    @property
    def loader(self):
        if self._loader is None:
            from src.repository_loader import RepositoryLoader
            self._loader = RepositoryLoader()
        return self._loader

    @property
    def extractor(self):
        if self._extractor is None:
            from src.knowledge_extractor import KnowledgeExtractor
            self._extractor = KnowledgeExtractor()
        return self._extractor

    @property
    def builder(self):
        if self._builder is None:
            from src.graph_builder import GraphBuilder
            self._builder = GraphBuilder(str(self.output_dir))
        return self._builder

    def _make_qa(self, graph):
        from src.qa_engine import QAEngine
        return QAEngine(graph)

    def _make_doc(self, path, title, content, headings):
        from src.models import Document
        return Document(path=path, title=title, content=content, headings=headings)

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
                    
                    documents.append(self._make_doc(
                        str(relative_path), title, content, headings
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
        self.qa_engine = self._make_qa(graph)
        
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

    def analyze_incremental(self, path: str, recursive: bool = True) -> dict:
        from src.models import FileRecord
        path = Path(path)
        if not path.exists():
            console.print(f"[red]✗ 路径不存在: {path}[/red]")
            return None

        repo_name = path.name
        self.project_name = repo_name
        manifest_path = self.output_dir / f"{repo_name}.manifest.json"

        console.print(f"\n[bold]📂 增量分析: [cyan]{path}[/cyan][/bold]\n")

        from src.incremental import IncrementalAnalyzer
        incremental = IncrementalAnalyzer(self.extractor, manifest_path)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task1 = progress.add_task("[cyan]扫描文件...", total=None)
            md_files_raw = self._find_markdown_files(path, recursive)
            code_files_raw = self._find_code_files(path, recursive)
            progress.update(task1, completed=100,
                            description=f"[green]✓ 找到 {len(md_files_raw)} 个 Markdown, {len(code_files_raw)} 个代码文件")

            task2 = progress.add_task("[cyan]读取文件内容...", total=len(md_files_raw) + len(code_files_raw))
            md_files: list[tuple[str, str]] = []
            for f in md_files_raw:
                try:
                    content = self._read_file(f)
                    md_files.append((str(f.relative_to(path)), content))
                except Exception as e:
                    console.print(f"[yellow]⚠ 读取失败 {f}: {e}[/yellow]")
                progress.advance(task2)
            code_files: list[tuple[str, str]] = []
            for f in code_files_raw:
                try:
                    content = self._read_file(f)
                    code_files.append((str(f.relative_to(path)), content))
                except Exception as e:
                    console.print(f"[yellow]⚠ 读取失败 {f}: {e}[/yellow]")
                progress.advance(task2)

            task3 = progress.add_task("[cyan]检测变化...", total=None)
            current = incremental.compute_current_files(md_files, code_files)
            manifest = incremental.load_manifest()
            added, modified, deleted = incremental.detect_changes(current, manifest)
            progress.update(task3, completed=100, description=f"[green]✓ 新增 {len(added)}, 修改 {len(modified)}, 删除 {len(deleted)}")

        if not added and not modified and not deleted:
            console.print("[green]✓ 没有文件变化，无需更新[/green]")
            try:
                graph = self.builder.load_graph(repo_name)
                self.current_graph = graph
                self.qa_engine = self._make_qa(graph)
            except FileNotFoundError:
                pass
            return None

        changed = set(added + modified)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task4 = progress.add_task("[cyan]增量提取...", total=None)
            new_entities, new_relations = incremental.extract_from_files(changed, md_files, code_files)
            progress.update(task4, completed=100,
                            description=f"[green]✓ 提取 {len(new_entities)} 个实体, {len(new_relations)} 个关系")

            task5 = progress.add_task("[cyan]合并图谱...", total=None)
            try:
                graph = self.builder.load_graph(repo_name)
            except FileNotFoundError:
                from src.models import KnowledgeGraph
                graph = KnowledgeGraph()

            for fp in deleted:
                graph = incremental.remove_file_from_graph(graph, fp)

            graph = incremental.merge(graph, new_entities, new_relations)
            progress.update(task5, completed=100, description="[green]✓ 合并完成")

        output_file = self.output_dir / f"{repo_name}.graph.json"
        import json
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(graph.model_dump(), f, ensure_ascii=False, indent=2)

        html_path = self.builder.generate_html_visualization(graph, repo_name)

        new_manifest = incremental.load_manifest()
        existing = {r.path: r for r in new_manifest.files}
        for p, h in current.items():
            existing[p] = FileRecord(path=p, content_hash=h)
        for fp in deleted:
            existing.pop(fp, None)
        from src.models import FileManifest as _FM
        incremental.save_manifest(_FM(files=list(existing.values())))

        self.current_graph = graph
        self.qa_engine = self._make_qa(graph)

        console.print()
        console.print(Panel(
            f"[bold green]✓ 增量更新完成![/bold green]\n\n"
            f"  ➕ 新增: [cyan]{len(added)}[/cyan] 个文件\n"
            f"  ✏️ 修改: [cyan]{len(modified)}[/cyan] 个文件\n"
            f"  🗑️ 删除: [cyan]{len(deleted)}[/cyan] 个文件\n"
            f"  📊 实体: [cyan]{len(graph.entities)}[/cyan] 个\n"
            f"  🔗 关系: [cyan]{len(graph.relations)}[/cyan] 个",
            title="[bold]增量分析结果[/bold]",
            border_style="green",
        ))

        return {
            "name": repo_name,
            "added": len(added),
            "modified": len(modified),
            "deleted": len(deleted),
            "entities": len(graph.entities),
            "relations": len(graph.relations),
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
        from src.models import EntityType
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
            self.qa_engine = self._make_qa(graph)
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

    def load_graph_by_name(self, project: str = None) -> bool:
        """加载图谱，支持指定项目名，默认加载第一个"""
        graphs = self.list_graphs()
        if not graphs:
            console.print("[red]没有找到已分析的项目[/red]")
            return False
        if project:
            if project not in graphs:
                console.print(f"[red]找不到项目: {project}[/red]")
                console.print(f"[dim]可用项目: {', '.join(graphs)}[/dim]")
                return False
            return self.load_graph(project)
        return self.load_graph(graphs[0])

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

    def analyze_flows(self, path: str) -> None:
        """分析API流程"""
        path = Path(path)
        
        if not path.exists():
            console.print(f"[red]✗ 路径不存在: {path}[/red]")
            return
        
        self.current_path = path
        
        # 保存路径信息
        flow_info_path = self.output_dir / "flow_info.json"
        with open(flow_info_path, 'w', encoding='utf-8') as f:
            json.dump({"path": str(path)}, f)
        
        console.print(f"\n[bold]🔍 分析API流程: [cyan]{path}[/cyan][/bold]\n")
        
        # 查找代码文件
        code_files = []
        extensions = {'.py', '.js', '.ts', '.java', '.go'}
        ignore_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv'}
        
        for root, dirs, filenames in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for f in filenames:
                if Path(f).suffix in extensions:
                    file_path = Path(root) / f
                    try:
                        content = self._read_file(file_path)
                        relative_path = str(file_path.relative_to(path))
                        code_files.append((relative_path, content))
                    except Exception as e:
                        console.print(f"[yellow]⚠ 读取失败: {file_path}: {e}[/yellow]")
        
        console.print(f"找到 [green]{len(code_files)}[/green] 个代码文件\n")
        
        # 分析流程
        from src.flow_analyzer import analyze_project_flows
        with console.status("[bold green]分析API流程..."):
            self.flow_analyzer = analyze_project_flows(code_files)
        
        # 保存分析结果
        self._save_flow_analysis()
        
        # 显示结果
        self.show_flow_summary()
    
    def _save_flow_analysis(self) -> None:
        """保存流程分析结果"""
        if not self.flow_analyzer:
            return
        
        # 保存API端点信息
        endpoints_data = []
        for ep in self.flow_analyzer.api_endpoints:
            endpoints_data.append({
                "method": ep.method,
                "path": ep.path,
                "handler": ep.handler,
                "file": ep.file_path,
                "steps": ep.steps
            })
        
        with open(self.output_dir / "api_endpoints.json", 'w', encoding='utf-8') as f:
            json.dump(endpoints_data, f, ensure_ascii=False, indent=2)
    
    def _load_flow_analysis(self) -> bool:
        """加载流程分析结果"""
        flow_info_path = self.output_dir / "flow_info.json"
        endpoints_path = self.output_dir / "api_endpoints.json"
        
        if not flow_info_path.exists() or not endpoints_path.exists():
            return False
        
        # 加载路径信息
        with open(flow_info_path, 'r', encoding='utf-8') as f:
            info = json.load(f)
            self.current_path = Path(info["path"])
        
        # 重新分析
        self.analyze_flows(str(self.current_path))
        return True
    
    def show_flow_summary(self) -> None:
        """显示流程分析摘要"""
        if not self.flow_analyzer:
            console.print("[red]请先分析项目流程[/red]")
            return
        
        analyzer = self.flow_analyzer
        
        # API端点统计
        endpoints = analyzer.api_endpoints
        functions = analyzer.functions
        
        console.print()
        
        # 显示统计信息
        stats_table = Table(
            title="[bold]📊 流程分析统计[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        stats_table.add_column("指标", style="cyan")
        stats_table.add_column("数量", style="green", justify="right")
        
        stats_table.add_row("API端点", str(len(endpoints)))
        stats_table.add_row("函数", str(len(functions)))
        stats_table.add_row("代码文件", str(len(set(f.file_path for f in functions.values()))))
        
        console.print(stats_table)
        
        # 显示API列表
        if endpoints:
            console.print()
            api_table = Table(
                title="[bold]🌐 API端点[/bold]",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan"
            )
            api_table.add_column("#", style="dim", width=4)
            api_table.add_column("方法", style="bold")
            api_table.add_column("路径", style="cyan")
            api_table.add_column("处理函数", style="green")
            api_table.add_column("步骤数", style="yellow", justify="right")
            api_table.add_column("文件", style="dim")
            
            for i, endpoint in enumerate(endpoints, 1):
                method_colors = {
                    'GET': 'green',
                    'POST': 'blue',
                    'PUT': 'yellow',
                    'DELETE': 'red',
                    'PATCH': 'magenta'
                }
                method_color = method_colors.get(endpoint.method, 'white')
                
                api_table.add_row(
                    str(i),
                    f"[{method_color}]{endpoint.method}[/{method_color}]",
                    endpoint.path,
                    endpoint.handler,
                    str(len(endpoint.steps)),
                    endpoint.file_path
                )
            
            console.print(api_table)
    
    def show_flow_detail(self, index: int) -> None:
        """显示特定API的流程详情"""
        if not self.flow_analyzer:
            console.print("[red]请先分析项目流程[/red]")
            return
        
        endpoints = self.flow_analyzer.api_endpoints
        
        if index < 1 or index > len(endpoints):
            console.print(f"[red]无效的索引: {index}[/red]")
            return
        
        endpoint = endpoints[index - 1]
        
        console.print()
        console.print(Panel(
            f"[bold]{endpoint.method} {endpoint.path}[/bold]\n\n"
            f"  处理函数: [cyan]{endpoint.handler}[/cyan]\n"
            f"  文件: [dim]{endpoint.file_path}[/dim]\n"
            f"  步骤数: [green]{len(endpoint.steps)}[/green]",
            title="[bold]API详情[/bold]",
            border_style="cyan"
        ))
        
        # 显示调用链
        if endpoint.steps:
            console.print()
            tree = Tree("[bold]📞 调用链[/bold]")
            
            for i, step in enumerate(endpoint.steps):
                func_info = self.flow_analyzer.functions.get(step)
                if func_info:
                    desc = func_info.description or ""
                    file_info = f"[dim]{func_info.file_path}[/dim]"
                    node_text = f"[cyan]{step}[/cyan]"
                    if desc:
                        node_text += f" - [green]{desc}[/green]"
                    node_text += f" {file_info}"
                    tree.add(node_text)
                else:
                    tree.add(f"[cyan]{step}[/cyan]")
            
            console.print(tree)
    
    def generate_flowchart(self, index: int = None, output: str = None) -> None:
        """生成Mermaid流程图"""
        if not self.flow_analyzer:
            console.print("[red]请先分析项目流程[/red]")
            return
        
        # 生成Mermaid代码
        mermaid = self.flow_analyzer.generate_mermaid_flowchart(index - 1 if index else None)
        
        # 确定输出文件
        if not output:
            if index:
                endpoints = self.flow_analyzer.api_endpoints
                if 1 <= index <= len(endpoints):
                    endpoint = endpoints[index - 1]
                    safe_name = f"{endpoint.method}_{endpoint.path}".replace('/', '_').replace('{', '').replace('}', '')
                    output = f"flow_{safe_name}.md"
                else:
                    output = "flow.md"
            else:
                output = "flow.md"
        
        # 保存文件
        with open(output, 'w', encoding='utf-8') as f:
            f.write("# API流程图\n\n")
            f.write("```mermaid\n")
            f.write(mermaid)
            f.write("\n```\n\n")
            f.write("## 使用方法\n\n")
            f.write("1. 复制上面的Mermaid代码\n")
            f.write("2. 打开 [Mermaid Live Editor](https://mermaid.live)\n")
            f.write("3. 粘贴代码即可查看流程图\n\n")
            f.write("或者安装 VS Code 的 Mermaid 插件直接预览。\n")
        
        console.print(f"[green]✓ 流程图已生成: {output}[/green]")
    
    def generate_all_flowcharts(self, output_dir: str = None) -> None:
        """为每个API生成单独的流程图"""
        if not self.flow_analyzer:
            console.print("[red]请先分析项目流程[/red]")
            return
        
        if not output_dir:
            output_dir = "flowcharts"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        flowcharts = self.flow_analyzer.generate_all_flowcharts()
        
        for name, mermaid in flowcharts.items():
            safe_name = name.replace('/', '_').replace('{', '').replace('}', '').replace(' ', '_')
            file_path = output_path / f"{safe_name}.md"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {name} 流程图\n\n")
                f.write("```mermaid\n")
                f.write(mermaid)
                f.write("\n```\n")
        
        console.print(f"[green]✓ 已生成 {len(flowcharts)} 个流程图到 {output_dir}/ 目录[/green]")

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
        from src.renderers import render_report_markdown
        content = render_report_markdown(self.current_graph, self.project_name or '项目')
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)

    def _export_html(self, output: str):
        """导出为HTML报告"""
        from src.renderers import render_report_html
        content = render_report_html(self.current_graph, self.project_name or '项目')
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)


# CLI 命令
@click.group()
@click.option('--output', '-o', default='output', help='输出目录')
@click.option('--project', '-p', default=None, help='指定项目名称（默认加载第一个）')
@click.pass_context
def cli(ctx, output, project):
    """[bold cyan]RepoMind[/bold cyan] - 智能项目知识图谱生成工具"""
    ctx.ensure_object(dict)
    ctx.obj['kg'] = KnowledgeGraphCLI(output)
    ctx.obj['project'] = project


@cli.command()
@click.argument('path')
@click.option('--no-recursive', is_flag=True, help='不递归扫描子目录')
@click.option('--incremental', '-i', is_flag=True, help='增量更新（只处理变化的文件）')
@click.option('--llm', is_flag=True, help='使用 LLM 提取知识（需要 OPENAI_API_KEY）')
@click.option('--model', default=None, help='LLM 模型名称（默认读取 OPENAI_MODEL 环境变量）')
@click.option('--api-key', default=None, help='API Key（默认读取 OPENAI_API_KEY 环境变量）')
@click.option('--base-url', default=None, help='API Base URL（默认读取 OPENAI_BASE_URL 环境变量）')
@click.pass_context
def analyze(ctx, path, no_recursive, incremental, llm, model, api_key, base_url):
    """分析本地目录，生成知识图谱"""
    from src.client import is_daemon_running

    llm_opts = {"llm": llm, "model": model, "api_key": api_key, "base_url": base_url} if llm else {}

    if is_daemon_running(port=DAEMON_PORT):
        result = _analyze_via_daemon(path, incremental, not no_recursive, llm_opts)
    else:
        kg = ctx.obj['kg']
        if llm:
            from src.llm_extractor import LLMExtractor
            kg._extractor = LLMExtractor(api_key=api_key, model=model, base_url=base_url)
        if incremental:
            result = kg.analyze_incremental(path, recursive=not no_recursive)
        else:
            result = kg.analyze(path, recursive=not no_recursive)

    if result:
        console.print("\n[bold]💡 下一步操作:[/bold]")
        console.print("  [cyan]python cli.py summary[/cyan]       查看分析摘要")
        console.print("  [cyan]python cli.py query <问题>[/cyan]   查询知识图谱")
        console.print("  [cyan]python cli.py interactive[/cyan]   进入交互模式")


def _analyze_via_daemon(path, incremental, recursive, llm_opts=None):
    from src.client import request_streaming
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

    result_data = {}
    steps = {}

    def on_event(event):
        etype = event.get("event")
        if etype == "step":
            step = event["step"]
            status = event["status"]
            if status == "start":
                label = {"scan": "扫描文件", "read": "读取文件", "diff": "检测变化",
                         "extract": "提取知识图谱", "build": "构建图谱", "merge": "合并图谱"
                         }.get(step, step)
                total = event.get("total")
                task_id = progress.add_task(f"[cyan]{label}...", total=total)
                steps[step] = task_id
            elif status == "done":
                task_id = steps.get(step)
                if task_id is not None:
                    label = {"scan": "扫描完成", "read": "读取完成", "diff": "检测完成",
                             "extract": "提取完成", "build": "构建完成", "merge": "合并完成"
                             }.get(step, step)
                    extra = ""
                    if "md_count" in event:
                        extra = f" ({event['md_count']} md, {event['code_count']} code)"
                    elif "entity_count" in event:
                        extra = f" ({event['entity_count']} 实体, {event['relation_count']} 关系)"
                    elif "added" in event:
                        extra = f" (+{event['added']} ~{event['modified']} -{event['deleted']})"
                    progress.update(task_id, completed=steps.get(step + "_total", 100),
                                    description=f"[green]✓ {label}{extra}")
        elif etype == "progress":
            step = event["step"]
            task_id = steps.get(step)
            if task_id is not None:
                progress.advance(task_id)
        elif etype == "result":
            result_data.update(event.get("data", {}))
        elif etype == "error":
            console.print(f"[red]✗ {event.get('error')}[/red]")

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(), console=console,
    ) as progress:
        resp = request_streaming("analyze", {
            "path": path, "incremental": incremental, "recursive": recursive,
            **(llm_opts or {}),
        }, on_event=on_event, port=DAEMON_PORT)

    if "error" in resp:
        console.print(f"[red]✗ {resp['error']}[/red]")
        return None

    result = resp.get("result", result_data)
    if not result:
        return None

    if result.get("no_change"):
        console.print("[green]✓ 没有文件变化，无需更新[/green]")
        return None

    console.print()
    if incremental:
        console.print(Panel(
            f"[bold green]✓ 增量更新完成![/bold green]\n\n"
            f"  ➕ 新增: [cyan]{result.get('added', 0)}[/cyan] 个文件\n"
            f"  ✏️ 修改: [cyan]{result.get('modified', 0)}[/cyan] 个文件\n"
            f"  🗑️ 删除: [cyan]{result.get('deleted', 0)}[/cyan] 个文件\n"
            f"  📊 实体: [cyan]{result.get('entities', 0)}[/cyan] 个\n"
            f"  🔗 关系: [cyan]{result.get('relations', 0)}[/cyan] 个",
            title="[bold]增量分析结果[/bold]", border_style="green",
        ))
    else:
        console.print(Panel(
            f"[bold green]✓ 分析完成![/bold green]\n\n"
            f"  📊 实体: [cyan]{result.get('entities', 0)}[/cyan] 个\n"
            f"  🔗 关系: [cyan]{result.get('relations', 0)}[/cyan] 个\n"
            f"  📁 图谱: [dim]{result.get('graph_path', '')}[/dim]\n"
            f"  🌐 可视化: [dim]{result.get('html_path', '')}[/dim]",
            title="[bold]分析结果[/bold]", border_style="green",
        ))

    return result


@cli.command()
@click.pass_context
def summary(ctx):
    """显示当前项目的分析摘要"""
    project = ctx.obj.get('project')
    result = _try_daemon("summary", {"project": project})
    if result == "error":
        return
    if result is not None:
        if isinstance(result, dict) and "error" in result:
            console.print(f"[red]{result['error']}[/red]")
            return
        _display_summary(result)
        return
    kg = ctx.obj['kg']
    if kg.load_graph_by_name(project):
        kg.show_summary()


def _display_summary(data):
    from rich import box
    table = Table(
        title=f"[bold]📊 {data.get('project', '项目')} 分析报告[/bold]",
        box=box.ROUNDED, show_header=True, header_style="bold magenta"
    )
    table.add_column("类型", style="cyan", width=15)
    table.add_column("图标", width=4)
    table.add_column("数量", style="green", justify="right", width=8)
    table.add_column("占比", style="yellow", justify="right", width=8)
    total = data.get("entities", 0)
    for type_name, count in sorted(data.get("types", {}).items(), key=lambda x: -x[1]):
        icon = ENTITY_ICONS.get(type_name, "•")
        pct = f"{count/total*100:.1f}%" if total else "0%"
        table.add_row(type_name, icon, str(count), pct)
    table.add_section()
    table.add_row("[bold]总计[/bold]", "📊", f"[bold]{total}[/bold]", "100%")
    console.print()
    console.print(table)
    modules = data.get("modules", [])
    if modules:
        console.print()
        tree = Tree("[bold]📦 核心模块[/bold]")
        for m in modules:
            tree.add(f"[cyan]{m}[/cyan]")
        console.print(tree)


@cli.command()
@click.argument('question')
@click.pass_context
def query(ctx, question):
    """查询知识图谱"""
    project = ctx.obj.get('project')
    result = _try_daemon("query", {"question": question, "project": project})
    if result == "error":
        return
    if result is not None:
        answer = result.get("answer", "") if isinstance(result, dict) else str(result)
        console.print()
        console.print(Panel(answer, title="[bold]💬 回答[/bold]", border_style="green", padding=(1, 2)))
        return
    kg = ctx.obj['kg']
    if not kg.load_graph_by_name(project):
        return
    answer = kg.query(question)
    console.print()
    console.print(Panel(answer, title="[bold]💬 回答[/bold]", border_style="green", padding=(1, 2)))


@cli.command()
@click.argument('keyword')
@click.pass_context
def search(ctx, keyword):
    """搜索实体"""
    project = ctx.obj.get('project')
    result = _try_daemon("search", {"keyword": keyword, "project": project})
    if result == "error":
        return
    if result is not None:
        results = result.get("results", []) if isinstance(result, dict) else []
        if not results:
            console.print(f"[yellow]没有找到包含 '{keyword}' 的实体[/yellow]")
            return
        from rich import box
        table = Table(title=f"[bold]🔍 搜索结果: '{keyword}'[/bold]", box=box.ROUNDED)
        table.add_column("名称", style="cyan")
        table.add_column("类型", style="magenta")
        table.add_column("描述", style="dim")
        for e in results:
            icon = ENTITY_ICONS.get(e["type"], "•")
            desc = (e["description"][:30] + "...") if e["description"] and len(e["description"]) > 30 else (e["description"] or "-")
            table.add_row(f"{icon} {e['name']}", e["type"], desc)
        console.print()
        console.print(table)
        return
    kg = ctx.obj['kg']
    project = ctx.obj.get('project')
    if kg.load_graph_by_name(project):
        kg.search(keyword)


@cli.command()
@click.argument('name')
@click.pass_context
def entity(ctx, name):
    """查看实体详情"""
    project = ctx.obj.get('project')
    result = _try_daemon("entity", {"name": name, "project": project})
    if result == "error":
        return
    if result is not None:
        if isinstance(result, dict) and "error" in result:
            console.print(f"[red]{result['error']}[/red]")
            return
        icon = ENTITY_ICONS.get(result["type"], "•")
        console.print()
        console.print(Panel(
            f"[bold]{icon} {result['name']}[/bold]\n\n"
            f"  类型: [cyan]{result['type']}[/cyan]\n"
            f"  描述: [dim]{result['description'] or '-'}[/dim]\n"
            f"  来源: [green]{result['source_file'] or '-'}[/green]",
            title="[bold]实体详情[/bold]", border_style="cyan"
        ))
        rels = result.get("relations", [])
        if rels:
            from rich import box
            rel_table = Table(title="[bold]相关关系[/bold]", box=box.SIMPLE)
            rel_table.add_column("方向", style="cyan", width=8)
            rel_table.add_column("关系", style="magenta", width=12)
            rel_table.add_column("实体", style="green")
            for r in rels:
                if r["direction"] == "out":
                    rel_table.add_row("→ 出", r["type"], r["target"])
                else:
                    rel_table.add_row("← 入", r["type"], r["source"])
            console.print()
            console.print(rel_table)
        return
    kg = ctx.obj['kg']
    if kg.load_graph_by_name(project):
        kg.show_entity(name)


@cli.command()
@click.argument('name')
@click.pass_context
def deps(ctx, name):
    """查看依赖关系"""
    project = ctx.obj.get('project')
    result = _try_daemon("deps", {"name": name, "project": project})
    if result == "error":
        return
    if result is not None:
        if isinstance(result, dict) and "error" in result:
            console.print(f"[red]{result['error']}[/red]")
            return
        tree = Tree(f"[bold cyan]{name}[/bold cyan] 依赖关系")
        dep_list = result.get("dependencies", [])
        dep_in = result.get("dependents", [])
        if dep_list:
            branch = tree.add("[bold]依赖 →[/bold]")
            for d in dep_list:
                branch.add(f"[green]{d}[/green]")
        if dep_in:
            branch = tree.add("[bold]被依赖 ←[/bold]")
            for d in dep_in:
                branch.add(f"[yellow]{d}[/yellow]")
        if not dep_list and not dep_in:
            tree.add("[dim]无依赖关系[/dim]")
        console.print()
        console.print(tree)
        return
    kg = ctx.obj['kg']
    if kg.load_graph_by_name(project):
        kg.show_dependencies(name)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'markdown', 'html']), default='json', help='导出格式')
@click.option('--output', '-o', help='输出文件路径')
@click.pass_context
def export(ctx, format, output):
    """导出知识图谱"""
    project = ctx.obj.get('project')
    result = _try_daemon("export", {"format": format, "output": output, "project": project})
    if result == "error":
        return
    if result is not None:
        path = result.get("exported", "") if isinstance(result, dict) else ""
        console.print(f"[green]✓ 已导出到: {path}[/green]")
        return
    kg = ctx.obj['kg']
    if kg.load_graph_by_name(project):
        kg.export(format, output)


@cli.command(name='list')
@click.pass_context
def list_graphs(ctx):
    """列出所有已生成的知识图谱"""
    result = _try_daemon("list")
    if result == "error":
        return
    if result is not None:
        graphs = result.get("graphs", []) if isinstance(result, dict) else []
    else:
        kg = ctx.obj['kg']
        graphs = kg.list_graphs()
    
    if not graphs:
        console.print("[yellow]没有找到已分析的项目[/yellow]")
        return
    
    from rich import box
    table = Table(
        title="[bold]📁 已分析的项目[/bold]",
        box=box.ROUNDED, show_header=True, header_style="bold magenta"
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
    result = _try_daemon("load", {"name": name})
    if result == "error":
        return
    if result is not None:
        if isinstance(result, dict) and "error" in result:
            console.print(f"[red]{result['error']}[/red]")
        else:
            console.print(f"[green]✓ 已加载: {name}[/green]")
        return
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
    project = ctx.obj.get('project')

    if not kg.load_graph_by_name(project):
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


@cli.command()
@click.argument('path')
@click.pass_context
def flow(ctx, path):
    """分析API流程"""
    kg = ctx.obj['kg']
    kg.analyze_flows(path)
    
    if kg.flow_analyzer:
        console.print("\n[bold]💡 下一步操作:[/bold]")
        console.print("  [cyan]python cli.py flow-detail -i <序号>[/cyan]  查看API详情")
        console.print("  [cyan]python cli.py flowchart -i <序号>[/cyan]   生成单个API流程图")
        console.print("  [cyan]python cli.py flowcharts[/cyan]            生成所有流程图")


@cli.command()
@click.option('--index', '-i', type=int, help='API索引')
@click.pass_context
def flow_detail(ctx, index):
    """显示API流程详情"""
    kg = ctx.obj['kg']
    
    if not kg.flow_analyzer:
        # 尝试加载之前的结果
        if not kg._load_flow_analysis():
            console.print("[red]请先运行 [cyan]flow[/cyan] 命令分析项目[/red]")
            return
    
    if not index:
        # 显示所有API
        kg.show_flow_summary()
        console.print("\n[bold]使用 [cyan]flow-detail -i <序号>[/cyan] 查看详情[/bold]")
    else:
        kg.show_flow_detail(index)


@cli.command()
@click.option('--index', '-i', type=int, help='API索引')
@click.option('--output', '-o', help='输出文件路径')
@click.pass_context
def flowchart(ctx, index, output):
    """生成Mermaid流程图"""
    kg = ctx.obj['kg']
    
    if not kg.flow_analyzer:
        # 尝试加载之前的结果
        if not kg._load_flow_analysis():
            console.print("[red]请先运行 [cyan]flow[/cyan] 命令分析项目[/red]")
            return
    
    kg.generate_flowchart(index, output)


@cli.command()
@click.option('--output-dir', '-d', default='flowcharts', help='输出目录')
@click.pass_context
def flowcharts(ctx, output_dir):
    """为所有API生成流程图"""
    kg = ctx.obj['kg']
    
    if not kg.flow_analyzer:
        # 尝试加载之前的结果
        if not kg._load_flow_analysis():
            console.print("[red]请先运行 [cyan]flow[/cyan] 命令分析项目[/red]")
            return
    
    kg.generate_all_flowcharts(output_dir)


@cli.command()
@click.option('--port', '-p', default=19832, help='监听端口')
@click.option('--host', default='127.0.0.1', help='监听地址')
@click.pass_context
def serve(ctx, port, host):
    """启动 daemon 服务器（常驻进程，消除重复启动开销）"""
    from src.server import run_server
    run_server(ctx.obj['kg'].output_dir, host, port)


@cli.command()
@click.option('--port', '-p', default=19832, help='daemon 端口')
@click.option('--host', default='127.0.0.1', help='daemon 地址')
def stop(port, host):
    """停止 daemon 服务器"""
    from src.client import request
    result = request("stop", host=host, port=port)
    if "error" in result:
        console.print(f"[red]✗ {result['error']}[/red]")
    else:
        console.print("[green]✓ Daemon 已停止[/green]")


if __name__ == '__main__':
    cli()