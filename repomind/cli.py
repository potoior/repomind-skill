#!/usr/bin/env python3
"""RepoMind - 智能项目知识图谱生成工具"""

import sys
import os
import io
import readline
import atexit
from pathlib import Path

def _load_dotenv():
    for p in [Path('.env'), Path.home() / '.repomind' / '.env']:
        if p.exists():
            for line in p.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_dotenv()

if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import click
import json
import time
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

# 确保当前目录在sys.path中（用于开发模式）
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

console = Console(force_terminal=True)

# ASCII Art Logo
LOGO = r"""
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
    from repomind.client import is_daemon_running, request
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
            from repomind.repository_loader import RepositoryLoader
            self._loader = RepositoryLoader()
        return self._loader

    @property
    def extractor(self):
        if self._extractor is None:
            from repomind.knowledge_extractor import KnowledgeExtractor
            self._extractor = KnowledgeExtractor()
        return self._extractor

    @property
    def builder(self):
        if self._builder is None:
            from repomind.graph_builder import GraphBuilder
            self._builder = GraphBuilder(str(self.output_dir))
        return self._builder

    def _make_qa(self, graph):
        from repomind.qa_engine import QAEngine
        return QAEngine(graph)

    def _make_doc(self, path, title, content, headings):
        from repomind.models import Document
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
        from repomind.models import FileRecord
        path = Path(path)
        if not path.exists():
            console.print(f"[red]✗ 路径不存在: {path}[/red]")
            return None

        repo_name = path.name
        self.project_name = repo_name
        manifest_path = self.output_dir / f"{repo_name}.manifest.json"

        console.print(f"\n[bold]📂 增量分析: [cyan]{path}[/cyan][/bold]\n")

        from repomind.incremental import IncrementalAnalyzer
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
                from repomind.models import KnowledgeGraph
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
        from repomind.models import FileManifest as _FM
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
        from repomind.models import EntityType
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
        from repomind.flow_analyzer import analyze_project_flows
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
        
        # 保存调用链信息
        chains_data = []
        for chain in self.flow_analyzer.call_chains:
            chains_data.append({
                "entry_point": chain.entry_point,
                "file": chain.file_path,
                "description": chain.description,
                "steps": chain.steps,
                "depth": chain.depth
            })
        
        with open(self.output_dir / "call_chains.json", 'w', encoding='utf-8') as f:
            json.dump(chains_data, f, ensure_ascii=False, indent=2)
    
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
        endpoints = analyzer.api_endpoints
        functions = analyzer.functions
        chains = analyzer.call_chains
        
        console.print()
        
        stats_table = Table(
            title="[bold]📊 流程分析统计[/bold]",
            box=box.ROUNDED, show_header=True, header_style="bold magenta"
        )
        stats_table.add_column("指标", style="cyan")
        stats_table.add_column("数量", style="green", justify="right")
        stats_table.add_row("API端点", str(len(endpoints)))
        stats_table.add_row("函数", str(len(functions)))
        stats_table.add_row("调用链", str(len(chains)))
        stats_table.add_row("代码文件", str(len(set(f.file_path for f in functions.values()))))
        console.print(stats_table)
        
        if endpoints:
            console.print()
            api_table = Table(
                title="[bold]🌐 API端点[/bold]",
                box=box.ROUNDED, show_header=True, header_style="bold cyan"
            )
            api_table.add_column("#", style="dim", width=4)
            api_table.add_column("方法", style="bold")
            api_table.add_column("路径", style="cyan")
            api_table.add_column("处理函数", style="green")
            api_table.add_column("步骤数", style="yellow", justify="right")
            api_table.add_column("文件", style="dim")
            
            for i, endpoint in enumerate(endpoints, 1):
                method_colors = {'GET': 'green', 'POST': 'blue', 'PUT': 'yellow', 'DELETE': 'red', 'PATCH': 'magenta'}
                method_color = method_colors.get(endpoint.method, 'white')
                api_table.add_row(
                    str(i), f"[{method_color}]{endpoint.method}[/{method_color}]",
                    endpoint.path, endpoint.handler, str(len(endpoint.steps)), endpoint.file_path
                )
            console.print(api_table)
        
        if chains:
            console.print()
            chain_table = Table(
                title="[bold]🔗 函数调用链[/bold]",
                box=box.ROUNDED, show_header=True, header_style="bold green"
            )
            chain_table.add_column("#", style="dim", width=4)
            chain_table.add_column("入口函数", style="cyan")
            chain_table.add_column("描述", style="dim")
            chain_table.add_column("深度", style="yellow", justify="right")
            chain_table.add_column("文件", style="dim")
            
            for i, chain in enumerate(chains[:15], 1):
                desc = (chain.description[:30] + "...") if chain.description and len(chain.description) > 30 else (chain.description or "-")
                chain_table.add_row(str(i), chain.entry_point, desc, str(chain.depth), chain.file_path)
            console.print(chain_table)
    
    def show_flow_detail(self, index: int) -> None:
        """显示特定API或调用链的流程详情"""
        if not self.flow_analyzer:
            console.print("[red]请先分析项目流程[/red]")
            return
        
        endpoints = self.flow_analyzer.api_endpoints
        chains = self.flow_analyzer.call_chains
        
        if index < 1:
            console.print(f"[red]无效的索引: {index}[/red]")
            return
        
        # API端点索引范围: 1..len(endpoints)
        if index <= len(endpoints):
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
        
        # 调用链索引范围: len(endpoints)+1 .. len(endpoints)+len(chains)
        elif index <= len(endpoints) + len(chains):
            chain_idx = index - len(endpoints) - 1
            chain = chains[chain_idx]
            
            console.print()
            console.print(Panel(
                f"[bold]{chain.entry_point}[/bold]\n\n"
                f"  文件: [dim]{chain.file_path}[/dim]\n"
                f"  描述: [green]{chain.description or '-'}[/green]\n"
                f"  深度: [yellow]{chain.depth}[/yellow]\n"
                f"  步骤数: [cyan]{len(chain.steps)}[/cyan]",
                title="[bold]调用链详情[/bold]",
                border_style="green"
            ))
            
            # 显示调用链步骤
            if chain.steps:
                console.print()
                tree = Tree("[bold]📞 调用链[/bold]")
                
                for i, step in enumerate(chain.steps):
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
        else:
            console.print(f"[red]无效的索引: {index}[/red]")
    
    def generate_flowchart(self, index: int = None, output: str = None) -> None:
        """生成Mermaid流程图"""
        if not self.flow_analyzer:
            console.print("[red]请先分析项目流程[/red]")
            return
        
        endpoints = self.flow_analyzer.api_endpoints
        chains = self.flow_analyzer.call_chains
        
        # 确定生成哪种类型的流程图
        is_call_chain = False
        chain_idx = None
        
        if index:
            if 1 <= index <= len(endpoints):
                # API端点流程图
                mermaid = self.flow_analyzer.generate_mermaid_flowchart(index - 1)
            elif len(endpoints) < index <= len(endpoints) + len(chains):
                # 调用链流程图
                is_call_chain = True
                chain_idx = index - len(endpoints) - 1
                mermaid = self.flow_analyzer.generate_call_chain_flowchart(chain_idx)
            else:
                console.print(f"[red]无效的索引: {index}[/red]")
                return
        else:
            # 生成所有流程图
            mermaid = self.flow_analyzer.generate_mermaid_flowchart()
        
        # 确定输出文件
        if not output:
            if index:
                if is_call_chain and chain_idx is not None:
                    chain = chains[chain_idx]
                    safe_name = chain.entry_point.replace('.', '_').replace('/', '_')
                    output = f"flow_call_{safe_name}.md"
                else:
                    endpoint = endpoints[index - 1]
                    safe_name = f"{endpoint.method}_{endpoint.path}".replace('/', '_').replace('{', '').replace('}', '')
                    output = f"flow_{safe_name}.md"
            else:
                output = "flow.md"
        
        # 保存文件
        title = "调用链流程图" if is_call_chain else "API流程图"
        with open(output, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
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
        from repomind.renderers import render_report_markdown
        content = render_report_markdown(self.current_graph, self.project_name or '项目')
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)

    def _export_html(self, output: str):
        """导出为HTML报告"""
        from repomind.renderers import render_report_html
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
    from repomind.client import is_daemon_running

    llm_opts = {"llm": llm, "model": model, "api_key": api_key, "base_url": base_url} if llm else {}

    if is_daemon_running(port=DAEMON_PORT):
        result = _analyze_via_daemon(path, incremental, not no_recursive, llm_opts)
    else:
        kg = ctx.obj['kg']
        if llm:
            from repomind.llm_extractor import LLMExtractor
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
    from repomind.client import request_streaming
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


@cli.command('batch-analyze')
@click.argument('paths', nargs=-1, required=True)
@click.option('--parent', '-p', is_flag=True, help='将第一个参数作为父目录，分析其所有子目录')
@click.option('--no-recursive', is_flag=True, help='不递归扫描子目录')
@click.option('--llm', is_flag=True, help='使用 LLM 提取知识（需要 OPENAI_API_KEY）')
@click.option('--model', default=None, help='LLM 模型名称')
@click.option('--api-key', default=None, help='API Key')
@click.option('--base-url', default=None, help='API Base URL')
@click.pass_context
def batch_analyze(ctx, paths, parent, no_recursive, llm, model, api_key, base_url):
    """批量分析多个目录
    
    示例:
      cli.py batch-analyze dir1 dir2 dir3
      cli.py batch-analyze ./projects --parent
    """
    from pathlib import Path
    
    # 确定要分析的目录列表
    if parent:
        parent_dir = Path(paths[0])
        if not parent_dir.exists():
            console.print(f"[red]✗ 父目录不存在: {parent_dir}[/red]")
            return
        if not parent_dir.is_dir():
            console.print(f"[red]✗ 不是目录: {parent_dir}[/red]")
            return
        
        # 获取所有子目录
        dirs = sorted([d for d in parent_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])
        if not dirs:
            console.print(f"[yellow]⚠ 父目录下没有找到子目录: {parent_dir}[/yellow]")
            return
        
        console.print(f"[bold]📂 批量分析: [cyan]{parent_dir}[/cyan] 下的 {len(dirs)} 个子目录[/bold]\n")
    else:
        dirs = [Path(p) for p in paths]
        for d in dirs:
            if not d.exists():
                console.print(f"[red]✗ 路径不存在: {d}[/red]")
                return
    
    # 分析每个目录
    results = []
    failed = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        main_task = progress.add_task("[bold]总进度...", total=len(dirs))
        
        for i, dir_path in enumerate(dirs):
            if not dir_path.is_dir():
                console.print(f"[yellow]⚠ 跳过非目录: {dir_path}[/yellow]")
                progress.advance(main_task)
                continue
            
            project_name = dir_path.name
            progress.update(main_task, description=f"[bold]分析 [{i+1}/{len(dirs)}]: [cyan]{project_name}[/cyan][/bold]")
            
            try:
                kg = ctx.obj['kg']
                
                # 设置 LLM 提取器
                if llm:
                    from repomind.llm_extractor import LLMExtractor
                    kg._extractor = LLMExtractor(api_key=api_key, model=model, base_url=base_url)
                
                # 执行分析
                result = kg.analyze(str(dir_path), recursive=not no_recursive)
                
                if result:
                    results.append({
                        'name': project_name,
                        'path': str(dir_path),
                        'entities': result.get('entities', 0),
                        'relations': result.get('relations', 0),
                    })
                else:
                    failed.append({'name': project_name, 'path': str(dir_path), 'error': '分析失败'})
            
            except Exception as e:
                failed.append({'name': project_name, 'path': str(dir_path), 'error': str(e)})
                console.print(f"[red]✗ {project_name}: {e}[/red]")
            
            progress.advance(main_task)
    
    # 显示汇总结果
    console.print()
    console.print(Panel(
        f"[bold green]✓ 批量分析完成![/bold green]\n\n"
        f"  成功: [cyan]{len(results)}[/cyan] 个\n"
        f"  失败: [red]{len(failed)}[/red] 个",
        title="[bold]批量分析结果[/bold]", border_style="green",
    ))
    
    # 显示详细结果表格
    if results:
        console.print()
        table = Table(
            title="[bold]📊 分析结果[/bold]",
            box=box.ROUNDED, show_header=True, header_style="bold magenta"
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("项目", style="cyan")
        table.add_column("实体", style="green", justify="right")
        table.add_column("关系", style="green", justify="right")
        table.add_column("路径", style="dim")
        
        total_entities = 0
        total_relations = 0
        
        for i, r in enumerate(results, 1):
            table.add_row(
                str(i), r['name'],
                str(r['entities']), str(r['relations']),
                r['path']
            )
            total_entities += r['entities']
            total_relations += r['relations']
        
        table.add_section()
        table.add_row(
            "", "[bold]总计[/bold]",
            f"[bold]{total_entities}[/bold]",
            f"[bold]{total_relations}[/bold]",
            ""
        )
        
        console.print(table)
    
    # 显示失败列表
    if failed:
        console.print()
        console.print("[bold red]❌ 失败列表:[/bold red]")
        for f in failed:
            console.print(f"  - {f['name']}: {f['error']}")
    
    # 提示下一步操作
    if results:
        console.print("\n[bold]💡 下一步操作:[/bold]")
        console.print("  [cyan]python cli.py list[/cyan]            查看所有项目")
        console.print("  [cyan]python cli.py -p <项目名> summary[/cyan]  查看项目摘要")
        console.print("  [cyan]python cli.py diff <旧> <新>[/cyan]  比较两个项目")


@cli.command()
@click.argument('path')
@click.option('--interval', '-i', default=2.0, help='检查间隔（秒）')
@click.option('--no-recursive', is_flag=True, help='不递归监听子目录')
@click.option('--llm', is_flag=True, help='使用 LLM 提取知识')
@click.option('--model', default=None, help='LLM 模型名称')
@click.option('--api-key', default=None, help='API Key')
@click.option('--base-url', default=None, help='API Base URL')
@click.pass_context
def watch(ctx, path, interval, no_recursive, llm, model, api_key, base_url):
    """监听文件变化，自动重新分析
    
    示例:
      cli.py watch ./my-project
      cli.py watch ./my-project --interval 5
    """
    from repomind.file_watcher import FileWatcher, WatchConfig, format_change_event
    
    # 验证路径
    watch_path = Path(path)
    if not watch_path.exists():
        console.print(f"[red]✗ 路径不存在: {path}[/red]")
        return
    
    if not watch_path.is_dir():
        console.print(f"[red]✗ 不是目录: {path}[/red]")
        return
    
    # 配置监听器
    config = WatchConfig(
        path=str(watch_path),
        recursive=not no_recursive
    )
    
    # 变更处理回调
    changes_buffer = []
    
    def on_change(event):
        """处理文件变更事件"""
        console.print(format_change_event(event))
        changes_buffer.append(event)
    
    # 创建监听器
    watcher = FileWatcher(config, on_change)
    
    console.print()
    console.print(Panel(
        f"[bold]👀 Watch 模式[/bold]\n\n"
        f"  监听路径: [cyan]{path}[/cyan]\n"
        f"  检查间隔: [yellow]{interval}秒[/yellow]\n"
        f"  递归监听: [green]{'是' if not no_recursive else '否'}[/green]\n\n"
        f"  [dim]按 Ctrl+C 停止监听[/dim]",
        title="[bold]开始监听[/bold]",
        border_style="cyan"
    ))
    
    # 首次分析
    console.print("\n[bold]📊 执行首次分析...[/bold]")
    kg = ctx.obj['kg']
    
    if llm:
        from repomind.llm_extractor import LLMExtractor
        kg._extractor = LLMExtractor(api_key=api_key, model=model, base_url=base_url)
    
    result = kg.analyze(str(watch_path), recursive=not no_recursive)
    
    if result:
        console.print(f"[green]✓ 首次分析完成: {result.get('entities', 0)} 实体, {result.get('relations', 0)} 关系[/green]")
    else:
        console.print("[yellow]⚠ 首次分析失败，继续监听...[/yellow]")
    
    # 开始监听
    console.print()
    
    try:
        watcher.running = True
        watcher.file_hashes = watcher.scan_directory()
        console.print(f"[green]✓ 开始监听: {len(watcher.file_hashes)} 个文件[/green]\n")
        
        last_analyze_time = 0
        analyze_cooldown = 5.0  # 分析冷却时间（秒）
        
        while watcher.running:
            changes = watcher.detect_changes()
            
            for change in changes:
                if watcher._debounce(change.path):
                    on_change(change)
            
            # 如果有变更且冷却时间已过，执行增量分析
            if changes_buffer and (time.time() - last_analyze_time) > analyze_cooldown:
                console.print(f"\n[bold]🔄 检测到 {len(changes_buffer)} 个变更，执行增量分析...[/bold]")
                
                try:
                    result = kg.analyze_incremental(str(watch_path), recursive=not no_recursive)
                    if result:
                        console.print(f"[green]✓ 增量分析完成: {result.get('entities', 0)} 实体, {result.get('relations', 0)} 关系[/green]")
                    else:
                        console.print("[yellow]⚠ 增量分析失败[/yellow]")
                except Exception as e:
                    console.print(f"[red]✗ 分析错误: {e}[/red]")
                
                changes_buffer.clear()
                last_analyze_time = time.time()
                console.print()
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 停止监听[/yellow]")
        watcher.running = False


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


@cli.command('search-advanced')
@click.argument('query')
@click.option('--type', '-t', 'entity_types', multiple=True, help='过滤实体类型（可多次指定）')
@click.option('--regex', '-r', is_flag=True, help='使用正则表达式')
@click.option('--fuzzy', '-f', is_flag=True, help='模糊匹配')
@click.option('--threshold', default=0.6, help='模糊匹配阈值 (0-1)')
@click.option('--case-sensitive', '-c', is_flag=True, help='区分大小写')
@click.option('--fields', default='name,description', help='搜索字段 (name,description)')
@click.option('--max-results', '-n', default=50, help='最大结果数')
@click.option('--context', is_flag=True, help='显示关联实体上下文')
@click.pass_context
def search_advanced(ctx, query, entity_types, regex, fuzzy, threshold, case_sensitive, fields, max_results, context):
    """高级搜索
    
    示例:
      cli.py search-advanced "UserService"
      cli.py search-advanced "user" -t Module -t Service
      cli.py search-advanced "^User.*" --regex
      cli.py search-advanced "uservic" --fuzzy --threshold 0.7
    """
    from repomind.advanced_search import search_entities, SearchOptions, format_search_results, search_with_context
    
    kg = ctx.obj['kg']
    project = ctx.obj.get('project')
    
    if not kg.load_graph_by_name(project):
        return
    
    # 构建搜索选项
    options = SearchOptions(
        query=query,
        entity_types=list(entity_types) if entity_types else None,
        case_sensitive=case_sensitive,
        use_regex=regex,
        fuzzy=fuzzy,
        fuzzy_threshold=threshold,
        search_fields=fields.split(','),
        max_results=max_results
    )
    
    # 执行搜索
    results = search_entities(kg.current_graph, options)
    
    if not results:
        console.print(f"[yellow]没有找到包含 '{query}' 的实体[/yellow]")
        return
    
    # 显示结果
    console.print()
    
    # 如果启用上下文模式，显示第一个结果的详细上下文
    if context and results:
        top_result = results[0]
        context_data = search_with_context(kg.current_graph, top_result.entity.name)
        
        if context_data:
            entity = context_data['entity']
            icon = ENTITY_ICONS.get(entity['type'], "•")
            
            console.print(Panel(
                f"[bold]{icon} {entity['name']}[/bold]\n\n"
                f"  类型: [cyan]{entity['type']}[/cyan]\n"
                f"  描述: [dim]{entity['description'] or '-'}[/dim]\n"
                f"  来源: [green]{entity['source_file'] or '-'}[/green]\n"
                f"  关联实体: [yellow]{context_data['related_count']}[/yellow] 个",
                title="[bold]最佳匹配[/bold]",
                border_style="cyan"
            ))
            
            # 显示出向关系
            if context_data['outgoing']:
                console.print()
                table = Table(title="[bold]➡️ 出向关系[/bold]", box=box.SIMPLE)
                table.add_column("关系", style="magenta")
                table.add_column("目标", style="cyan")
                table.add_column("类型", style="dim")
                
                for rel in context_data['outgoing'][:10]:
                    table.add_row(rel['relation'], rel['entity'], rel['type'])
                
                console.print(table)
            
            # 显示入向关系
            if context_data['incoming']:
                console.print()
                table = Table(title="[bold]⬅️ 入向关系[/bold]", box=box.SIMPLE)
                table.add_column("来源", style="cyan")
                table.add_column("关系", style="magenta")
                table.add_column("类型", style="dim")
                
                for rel in context_data['incoming'][:10]:
                    table.add_row(rel['entity'], rel['relation'], rel['type'])
                
                console.print(table)
    
    # 显示搜索结果列表
    table = Table(title=f"[bold]🔍 搜索结果: '{query}'[/bold]", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("名称", style="cyan")
    table.add_column("类型", style="magenta")
    table.add_column("描述", style="dim")
    table.add_column("匹配", style="green")
    table.add_column("分数", style="yellow", justify="right")
    
    for i, result in enumerate(results[:20], 1):
        entity = result.entity
        icon = ENTITY_ICONS.get(entity.type.value, "•")
        
        desc = (entity.description[:30] + "...") if entity.description and len(entity.description) > 30 else (entity.description or "-")
        
        table.add_row(
            str(i),
            f"{icon} {entity.name}",
            entity.type.value,
            desc,
            result.match_type,
            f"{result.score:.2f}"
        )
    
    console.print()
    console.print(table)
    
    if len(results) > 20:
        console.print(f"[dim]... 还有 {len(results) - 20} 个结果[/dim]")


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
    
    # 设置 readline 历史
    history_file = Path.home() / '.repomind' / 'history'
    history_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        readline.read_history_file(str(history_file))
    except FileNotFoundError:
        pass
    atexit.register(readline.write_history_file, str(history_file))
    readline.set_history_length(1000)
    
    # 设置 tab 补全
    def completer(text, state):
        commands = ['help', 'quit', 'exit', 'summary', 'search', 'relations', 
                    'deps', 'graph', 'flow', 'export', 'history', 'clear', 'modules',
                    'tech', 'databases', 'tools', 'documents']
        
        # 获取所有实体名称
        entities = [e.name for e in kg.current_graph.entities] if kg.current_graph else []
        all_options = commands + entities
        
        # 过滤匹配项
        matches = [opt for opt in all_options if opt.lower().startswith(text.lower())]
        
        if state < len(matches):
            return matches[state]
        return None
    
    readline.set_completer(completer)
    readline.parse_and_bind('tab: complete')
    
    console.print()
    console.print(Panel(
        "[bold]🔮 交互式查询模式[/bold]\n\n"
        "  [cyan]模块[/cyan] / [cyan]技术栈[/cyan] / [cyan]数据库[/cyan]  查看分类\n"
        "  [cyan]<名称>是什么[/cyan]                查看实体详情\n"
        "  [cyan]<名称>依赖什么[/cyan]              查看依赖关系\n"
        "  [cyan]search <关键词>[/cyan]              搜索实体\n"
        "  [cyan]relations <实体名>[/cyan]           查看实体关系\n"
        "  [cyan]deps <实体名>[/cyan]                查看依赖树\n"
        "  [cyan]graph <实体名>[/cyan]               生成实体关系图\n"
        "  [cyan]flow[/cyan]                         查看API流程\n"
        "  [cyan]export[/cyan]                       导出当前图谱\n"
        "  [cyan]history[/cyan]                      查看查询历史\n"
        "  [cyan]clear[/cyan]                        清屏\n"
        "  [cyan]summary[/cyan]                      查看摘要\n"
        "  [cyan]help[/cyan]                         显示帮助\n"
        "  [cyan]quit[/cyan]                         退出",
        title="[bold]使用说明[/bold]",
        border_style="cyan"
    ))
    
    query_history = []
    
    while True:
        try:
            question = console.input("\n[bold cyan]❯ [/bold cyan]")
            
            if not question.strip():
                continue
            
            query_history.append(question.strip())
            
            cmd = question.strip().lower()
            
            if cmd in ['quit', 'exit', 'q']:
                console.print("[yellow]👋 再见![/yellow]")
                break
            
            if cmd == 'summary':
                kg.show_summary()
                continue
            
            if cmd == 'help':
                _show_interactive_help()
                continue
            
            if cmd == 'clear':
                os.system('clear' if os.name != 'nt' else 'cls')
                continue
            
            if cmd == 'history':
                _show_query_history(query_history)
                continue
            
            if cmd.startswith('search '):
                keyword = question[7:].strip()
                kg.search(keyword)
                continue
            
            if cmd.startswith('relations '):
                entity_name = question[10:].strip()
                _show_relations(kg, entity_name)
                continue
            
            if cmd.startswith('deps '):
                entity_name = question[5:].strip()
                _show_dependency_tree(kg, entity_name)
                continue
            
            if cmd.startswith('graph '):
                entity_name = question[6:].strip()
                _generate_entity_graph(kg, entity_name)
                continue
            
            if cmd == 'flow':
                _show_flow_summary(kg)
                continue
            
            if cmd.startswith('flow '):
                try:
                    index = int(question[5:].strip())
                    _show_flow_detail(kg, index)
                except ValueError:
                    console.print("[red]请提供有效的索引号[/red]")
                continue
            
            if cmd == 'export':
                _export_interactive(kg)
                continue
            
            if cmd in ['modules', '模块']:
                _show_category(kg, 'Module', '📦')
                continue
            
            if cmd in ['tech', '技术栈']:
                _show_category(kg, 'Framework', '🔧')
                continue
            
            if cmd in ['databases', '数据库']:
                _show_category(kg, 'Database', '🗄️')
                continue
            
            if cmd in ['tools', '工具']:
                _show_category(kg, 'Tool', '🔨')
                continue
            
            if cmd in ['documents', '文档']:
                _show_category(kg, 'Document', '📄')
                continue
            
            # 默认使用 QA 引擎
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


def _show_interactive_help():
    """显示交互式模式帮助"""
    help_text = """[bold]可用命令:[/bold]

  [cyan]查询命令:[/cyan]
    <名称>是什么          查看实体详情
    <名称>依赖什么        查看依赖关系
    search <关键词>       搜索实体
    modules / 模块        查看所有模块
    tech / 技术栈         查看技术栈
    databases / 数据库    查看数据库
    tools / 工具          查看工具
    documents / 文档      查看文档

  [cyan]关系分析:[/cyan]
    relations <实体名>    查看实体的所有关系
    deps <实体名>         查看依赖树
    graph <实体名>        生成实体关系图

  [cyan]流程分析:[/cyan]
    flow                  查看API流程摘要
    flow <序号>           查看流程详情

  [cyan]其他命令:[/cyan]
    summary               查看项目摘要
    export                导出当前图谱
    history               查看查询历史
    clear                 清屏
    help                  显示此帮助
    quit / exit / q       退出"""
    
    console.print()
    console.print(Panel(help_text, title="[bold]帮助[/bold]", border_style="yellow"))


def _show_query_history(history: list):
    """显示查询历史"""
    if not history:
        console.print("[yellow]暂无查询历史[/yellow]")
        return
    
    console.print()
    table = Table(title="[bold]📜 查询历史[/bold]", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("查询", style="cyan")
    
    for i, q in enumerate(history[-20:], 1):
        table.add_row(str(i), q)
    
    console.print(table)


def _show_relations(kg, entity_name: str):
    """显示实体的所有关系"""
    if not kg.current_graph:
        console.print("[red]请先加载项目[/red]")
        return
    
    from repomind.query_engine import QueryEngine
    qe = QueryEngine(kg.current_graph)
    
    entity = qe.find_entity(entity_name)
    if not entity:
        # 尝试模糊匹配
        entities = qe.search_entities(entity_name)
        if entities:
            entity = entities[0]
            console.print(f"[yellow]未找到精确匹配，显示最相关的结果: {entity.name}[/yellow]")
        else:
            console.print(f"[red]找不到实体: {entity_name}[/red]")
            return
    
    relations = qe.find_relations(entity.name)
    
    if not relations:
        console.print(f"[yellow]{entity.name} 没有发现关系[/yellow]")
        return
    
    console.print()
    
    # 作为源的关系
    outgoing = [r for r in relations if r.source.lower() == entity.name.lower()]
    # 作为目标的关系
    incoming = [r for r in relations if r.target.lower() == entity.name.lower()]
    
    if outgoing:
        table = Table(title=f"[bold]➡️ {entity.name} 的出向关系[/bold]", box=box.ROUNDED)
        table.add_column("关系类型", style="magenta")
        table.add_column("目标", style="cyan")
        table.add_column("描述", style="dim")
        
        for r in outgoing:
            table.add_row(r.type.value, r.target, r.description or "-")
        
        console.print(table)
    
    if incoming:
        table = Table(title=f"[bold]⬅️ {entity.name} 的入向关系[/bold]", box=box.ROUNDED)
        table.add_column("来源", style="cyan")
        table.add_column("关系类型", style="magenta")
        table.add_column("描述", style="dim")
        
        for r in incoming:
            table.add_row(r.source, r.type.value, r.description or "-")
        
        console.print(table)


def _show_dependency_tree(kg, entity_name: str):
    """显示依赖树"""
    if not kg.current_graph:
        console.print("[red]请先加载项目[/red]")
        return
    
    from repomind.query_engine import QueryEngine
    qe = QueryEngine(kg.current_graph)
    
    entity = qe.find_entity(entity_name)
    if not entity:
        console.print(f"[red]找不到实体: {entity_name}[/red]")
        return
    
    deps = qe.find_dependencies(entity.name)
    
    if not deps:
        console.print(f"[yellow]{entity.name} 没有发现依赖[/yellow]")
        return
    
    console.print()
    tree = Tree(f"[bold]{entity.name}[/bold] 的依赖树")
    
    for dep in deps:
        icon = ENTITY_ICONS.get(dep.type.value, "•")
        node = tree.add(f"{icon} [cyan]{dep.name}[/cyan]")
        
        # 递归查找依赖的依赖
        sub_deps = qe.find_dependencies(dep.name)
        for sub_dep in sub_deps[:5]:
            sub_icon = ENTITY_ICONS.get(sub_dep.type.value, "•")
            node.add(f"{sub_icon} [dim]{sub_dep.name}[/dim]")
        
        if len(sub_deps) > 5:
            node.add(f"[dim]... 还有 {len(sub_deps) - 5} 个[/dim]")
    
    console.print(tree)


def _generate_entity_graph(kg, entity_name: str):
    """生成实体关系图"""
    if not kg.current_graph:
        console.print("[red]请先加载项目[/red]")
        return
    
    from repomind.query_engine import QueryEngine
    qe = QueryEngine(kg.current_graph)
    
    entity = qe.find_entity(entity_name)
    if not entity:
        console.print(f"[red]找不到实体: {entity_name}[/red]")
        return
    
    related = qe.find_related(entity.name)
    relations = qe.find_relations(entity.name)
    
    if not related and not relations:
        console.print(f"[yellow]{entity.name} 没有发现关联实体[/yellow]")
        return
    
    # 生成 Mermaid 图
    mermaid = "graph LR\n"
    mermaid += f"    {entity.name.replace('.', '_')}[\"{entity.name}\"]:::main\n"
    
    for rel in relations[:10]:
        target = rel.target if rel.source.lower() == entity.name.lower() else rel.source
        target_id = target.replace('.', '_')
        mermaid += f"    {target_id}[\"{target}\"]:::related\n"
        mermaid += f"    {entity.name.replace('.', '_')} -->|{rel.type.value}| {target_id}\n"
    
    mermaid += "    classDef main fill:#4CAF50,stroke:#388E3C,color:white\n"
    mermaid += "    classDef related fill:#2196F3,stroke:#1565C0,color:white\n"
    
    # 保存文件
    safe_name = entity.name.replace('.', '_').replace('/', '_')
    output = f"graph_{safe_name}.md"
    
    with open(output, 'w', encoding='utf-8') as f:
        f.write(f"# {entity.name} 关系图\n\n")
        f.write("```mermaid\n")
        f.write(mermaid)
        f.write("\n```\n")
    
    console.print(f"[green]✓ 关系图已生成: {output}[/green]")


def _show_flow_summary(kg):
    """显示流程摘要"""
    if not kg.flow_analyzer:
        console.print("[yellow]请先运行 flow 命令分析项目流程[/yellow]")
        return
    
    kg.show_flow_summary()


def _show_flow_detail(kg, index: int):
    """显示流程详情"""
    if not kg.flow_analyzer:
        console.print("[yellow]请先运行 flow 命令分析项目流程[/yellow]")
        return
    
    kg.show_flow_detail(index)


def _export_interactive(kg):
    """交互式导出"""
    if not kg.current_graph:
        console.print("[red]请先加载项目[/red]")
        return
    
    console.print()
    console.print("[bold]选择导出格式:[/bold]")
    console.print("  1. JSON")
    console.print("  2. CSV")
    console.print("  3. Markdown")
    console.print("  4. HTML")
    
    choice = console.input("\n[bold cyan]请选择 (1-4): [/bold cyan]")
    
    format_map = {'1': 'json', '2': 'csv', '3': 'markdown', '4': 'html'}
    fmt = format_map.get(choice, 'json')
    
    output = kg.export(fmt)
    if output:
        console.print(f"[green]✓ 已导出到: {output}[/green]")


def _show_category(kg, entity_type: str, icon: str):
    """显示分类实体"""
    if not kg.current_graph:
        console.print("[red]请先加载项目[/red]")
        return
    
    from repomind.models import EntityType
    from repomind.query_engine import QueryEngine
    
    qe = QueryEngine(kg.current_graph)
    
    try:
        etype = EntityType(entity_type)
    except ValueError:
        console.print(f"[red]未知的实体类型: {entity_type}[/red]")
        return
    
    entities = qe.find_entities_by_type(etype)
    
    if not entities:
        console.print(f"[yellow]项目中没有发现{entity_type}类型的实体[/yellow]")
        return
    
    console.print()
    table = Table(title=f"[bold]{icon} {entity_type}列表[/bold]", box=box.ROUNDED)
    table.add_column("名称", style="cyan")
    table.add_column("描述", style="dim")
    table.add_column("来源", style="green")
    
    for entity in entities[:20]:
        desc = (entity.description[:40] + "...") if entity.description and len(entity.description) > 40 else (entity.description or "-")
        table.add_row(entity.name, desc, entity.source_file or "-")
    
    console.print(table)
    
    if len(entities) > 20:
        console.print(f"[dim]... 还有 {len(entities) - 20} 个结果[/dim]")


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
@click.argument('old_project')
@click.argument('new_project')
@click.option('--detail', '-d', is_flag=True, help='显示详细差异')
@click.option('--json', 'output_json', is_flag=True, help='输出JSON格式')
@click.pass_context
def diff(ctx, old_project, new_project, detail, output_json):
    """比较两个知识图谱的差异
    
    示例: cli.py diff project-v1 project-v2
    """
    kg = ctx.obj['kg']
    
    from repomind.graph_diff import diff_graphs, format_diff_summary, format_diff_detail
    
    # 加载旧图谱
    if not kg.load_graph(old_project):
        console.print(f"[red]找不到项目: {old_project}[/red]")
        return
    old_graph = kg.current_graph
    
    # 加载新图谱
    if not kg.load_graph(new_project):
        console.print(f"[red]找不到项目: {new_project}[/red]")
        return
    new_graph = kg.current_graph
    
    # 计算差异
    graph_diff = diff_graphs(old_graph, new_graph)
    
    # 输出结果
    if output_json:
        import json
        console.print_json(json.dumps(graph_diff.model_dump(), ensure_ascii=False, indent=2))
    elif detail:
        console.print()
        console.print(format_diff_detail(graph_diff))
    else:
        console.print()
        console.print(format_diff_summary(graph_diff))
        
        if graph_diff.entity_changes or graph_diff.relation_changes:
            console.print("\n[dim]使用 -d 选项查看详细差异[/dim]")


@cli.command()
@click.argument('old_project')
@click.argument('new_project')
@click.option('--output', '-o', help='输出文件路径')
@click.pass_context
def diff_html(ctx, old_project, new_project, output):
    """生成图谱对比的HTML报告"""
    kg = ctx.obj['kg']
    
    from repomind.graph_diff import diff_graphs
    
    # 加载图谱
    if not kg.load_graph(old_project):
        console.print(f"[red]找不到项目: {old_project}[/red]")
        return
    old_graph = kg.current_graph
    
    if not kg.load_graph(new_project):
        console.print(f"[red]找不到项目: {new_project}[/red]")
        return
    new_graph = kg.current_graph
    
    # 计算差异
    graph_diff = diff_graphs(old_graph, new_graph)
    
    # 生成HTML报告
    html = _generate_diff_html(graph_diff, old_project, new_project)
    
    # 保存文件
    if not output:
        output = f"diff_{old_project}_vs_{new_project}.html"
    
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    
    console.print(f"[green]✓ 对比报告已生成: {output}[/green]")


def _generate_diff_html(diff, old_name: str, new_name: str) -> str:
    """生成对比报告的HTML"""
    from repomind.renderers import type_colors
    
    # 统计数据
    stats = {
        'entities_added': diff.entities_added,
        'entities_deleted': diff.entities_deleted,
        'entities_modified': diff.entities_modified,
        'relations_added': diff.relations_added,
        'relations_deleted': diff.relations_deleted,
    }
    
    # 实体变更
    entity_added = [c for c in diff.entity_changes if c.change_type == 'added']
    entity_deleted = [c for c in diff.entity_changes if c.change_type == 'deleted']
    entity_modified = [c for c in diff.entity_changes if c.change_type == 'modified']
    
    # 关系变更
    relation_added = [c for c in diff.relation_changes if c.change_type == 'added']
    relation_deleted = [c for c in diff.relation_changes if c.change_type == 'deleted']
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>图谱对比: {old_name} vs {new_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        .stats {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px; margin-bottom: 20px;
        }}
        .stat-card {{
            background: white; padding: 20px; border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;
        }}
        .stat-card .number {{ font-size: 36px; font-weight: bold; }}
        .stat-card .label {{ color: #666; margin-top: 5px; }}
        .stat-added .number {{ color: #27ae60; }}
        .stat-deleted .number {{ color: #e74c3c; }}
        .stat-modified .number {{ color: #f39c12; }}
        .section {{
            background: white; padding: 20px; border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px;
        }}
        .section h2 {{
            color: #333; margin-bottom: 15px;
            padding-bottom: 10px; border-bottom: 2px solid #667eea;
        }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; font-weight: 600; color: #333; }}
        tr:hover {{ background: #f5f5f5; }}
        .badge {{
            display: inline-block; padding: 4px 8px; border-radius: 4px;
            font-size: 12px; font-weight: 500;
        }}
        .badge-added {{ background: #d4edda; color: #155724; }}
        .badge-deleted {{ background: #f8d7da; color: #721c24; }}
        .badge-modified {{ background: #fff3cd; color: #856404; }}
        .empty {{ color: #888; font-style: italic; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 图谱对比报告</h1>
            <p>对比: {old_name} → {new_name}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card stat-added">
                <div class="number">+{diff.entities_added + diff.relations_added}</div>
                <div class="label">新增</div>
            </div>
            <div class="stat-card stat-deleted">
                <div class="number">-{diff.entities_deleted + diff.relations_deleted}</div>
                <div class="label">删除</div>
            </div>
            <div class="stat-card stat-modified">
                <div class="number">~{diff.entities_modified}</div>
                <div class="label">修改</div>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="number">{diff.old_entity_count}</div>
                <div class="label">旧图谱实体</div>
            </div>
            <div class="stat-card">
                <div class="number">{diff.new_entity_count}</div>
                <div class="label">新图谱实体</div>
            </div>
            <div class="stat-card">
                <div class="number">{diff.old_relation_count}</div>
                <div class="label">旧图谱关系</div>
            </div>
            <div class="stat-card">
                <div class="number">{diff.new_relation_count}</div>
                <div class="label">新图谱关系</div>
            </div>
        </div>
"""
    
    # 实体变更部分
    if entity_added or entity_deleted or entity_modified:
        html += """
        <div class="section">
            <h2>📦 实体变更</h2>
            <table>
                <tr><th>名称</th><th>类型</th><th>变更</th><th>描述</th></tr>
"""
        for c in entity_added:
            html += f"""
                <tr>
                    <td>{c.name}</td>
                    <td>{c.new_type}</td>
                    <td><span class="badge badge-added">新增</span></td>
                    <td>{c.new_description or '-'}</td>
                </tr>
"""
        for c in entity_deleted:
            html += f"""
                <tr>
                    <td>{c.name}</td>
                    <td>{c.old_type}</td>
                    <td><span class="badge badge-deleted">删除</span></td>
                    <td>{c.old_description or '-'}</td>
                </tr>
"""
        for c in entity_modified:
            changes = []
            if c.old_type != c.new_type:
                changes.append(f"类型: {c.old_type} → {c.new_type}")
            if c.old_description != c.new_description:
                changes.append(f"描述已修改")
            html += f"""
                <tr>
                    <td>{c.name}</td>
                    <td>{c.new_type}</td>
                    <td><span class="badge badge-modified">修改</span></td>
                    <td>{', '.join(changes) if changes else '-'}</td>
                </tr>
"""
        html += """
            </table>
        </div>
"""
    
    # 关系变更部分
    if relation_added or relation_deleted:
        html += """
        <div class="section">
            <h2>🔗 关系变更</h2>
            <table>
                <tr><th>源</th><th>关系</th><th>目标</th><th>变更</th></tr>
"""
        for c in relation_added:
            html += f"""
                <tr>
                    <td>{c.source}</td>
                    <td>{c.relation_type}</td>
                    <td>{c.target}</td>
                    <td><span class="badge badge-added">新增</span></td>
                </tr>
"""
        for c in relation_deleted:
            html += f"""
                <tr>
                    <td>{c.source}</td>
                    <td>{c.relation_type}</td>
                    <td>{c.target}</td>
                    <td><span class="badge badge-deleted">删除</span></td>
                </tr>
"""
        html += """
            </table>
        </div>
"""
    
    # 无变更
    if not diff.entity_changes and not diff.relation_changes:
        html += """
        <div class="section">
            <p class="empty">✅ 没有发现差异</p>
        </div>
"""
    
    html += """
    </div>
</body>
</html>"""
    
    return html


@cli.command()
@click.argument('projects', nargs=-1, required=True)
@click.option('--output', '-o', help='输出项目名称')
@click.option('--strategy', '-s', type=click.Choice(['skip', 'overwrite', 'keep_both']), 
              default='skip', help='冲突处理策略')
@click.option('--prefix', is_flag=True, help='在实体名前加项目前缀')
@click.pass_context
def merge(ctx, projects, output, strategy, prefix):
    """合并多个知识图谱
    
    示例:
      cli.py merge project1 project2 project3
      cli.py merge project1 project2 -o merged-project
      cli.py merge project1 project2 --strategy overwrite
    """
    kg = ctx.obj['kg']
    
    from repomind.graph_merge import merge_graphs, format_merge_summary, MergeOptions
    
    # 加载所有图谱
    graphs = []
    for project_name in projects:
        if not kg.load_graph(project_name):
            console.print(f"[red]找不到项目: {project_name}[/red]")
            return
        graphs.append((project_name, kg.current_graph))
    
    # 设置合并选项
    options = MergeOptions(
        conflict_strategy=strategy,
        prefix_project=prefix,
        deduplicate_relations=True
    )
    
    # 执行合并
    result = merge_graphs(graphs, options)
    
    # 显示合并摘要
    console.print()
    console.print(format_merge_summary(result))
    
    # 保存合并结果
    if not output:
        output = '-'.join(projects)
    
    # 保存图谱
    graph_path = kg.builder.save_graph(result.merged_graph, output)
    
    # 生成可视化
    from repomind.renderers import render_visjs_html
    html_content = render_visjs_html(result.merged_graph, output)
    html_path = kg.output_dir / f"{output}.graph.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    console.print()
    console.print(Panel(
        f"[bold green]✓ 合并完成![/bold green]\n\n"
        f"  📊 实体: [cyan]{len(result.merged_graph.entities)}[/cyan] 个\n"
        f"  🔗 关系: [cyan]{len(result.merged_graph.relations)}[/cyan] 个\n"
        f"  📁 图谱: [dim]{graph_path}[/dim]\n"
        f"  🌐 可视化: [dim]{html_path}[/dim]",
        title="[bold]合并结果[/bold]", border_style="green",
    ))
    
    # 提示下一步操作
    console.print("\n[bold]💡 下一步操作:[/bold]")
    console.print(f"  [cyan]python cli.py -p {output} summary[/cyan]    查看合并后的摘要")
    console.print(f"  [cyan]python cli.py -p {output} interactive[/cyan]  交互式查询")


@cli.command()
@click.option('--port', '-p', default=8000, help='Web服务端口')
@click.option('--host', default='127.0.0.1', help='监听地址')
@click.pass_context
def web(ctx, port, host):
    """启动Web UI（在线查询和图谱可视化）"""
    from repomind.web_ui import create_app
    
    output_dir = str(ctx.obj['kg'].output_dir)
    app = create_app(output_dir)
    
    console.print()
    console.print(Panel(
        f"[bold]🌐 RepoMind Web UI[/bold]\n\n"
        f"  地址: [cyan]http://{host}:{port}[/cyan]\n"
        f"  API文档: [cyan]http://{host}:{port}/docs[/cyan]\n\n"
        f"  [dim]按 Ctrl+C 停止服务[/dim]",
        title="[bold]启动Web服务[/bold]",
        border_style="green",
    ))
    
    try:
        import uvicorn
        uvicorn.run(app, host=host, port=port)
    except ImportError:
        console.print("[red]✗ 请安装 uvicorn: pip install uvicorn[/red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Web服务已停止[/yellow]")


@cli.command()
@click.option('--port', '-p', default=19832, help='监听端口')
@click.option('--host', default='127.0.0.1', help='监听地址')
@click.pass_context
def serve(ctx, port, host):
    """启动 daemon 服务器（常驻进程，消除重复启动开销）"""
    from repomind.server import run_server
    run_server(ctx.obj['kg'].output_dir, host, port)


@cli.command()
@click.option('--port', '-p', default=19832, help='daemon 端口')
@click.option('--host', default='127.0.0.1', help='daemon 地址')
def stop(port, host):
    """停止 daemon 服务器"""
    from repomind.client import request
    result = request("stop", host=host, port=port)
    if "error" in result:
        console.print(f"[red]✗ {result['error']}[/red]")
    else:
        console.print("[green]✓ Daemon 已停止[/green]")


@cli.command()
@click.argument('url')
@click.option('--branch', '-b', default=None, help='分支名称')
@click.option('--output', '-o', default='repos', help='克隆目录')
@click.pass_context
def clone(ctx, url, branch, output):
    """克隆GitHub仓库并分析
    
    示例:
      repomind clone https://github.com/owner/repo
      repomind clone owner/repo
      repomind clone git@github.com:owner/repo.git -b develop
    """
    from repomind.github_integration import parse_github_url, clone_repo, get_repo_info
    
    try:
        repo = parse_github_url(url)
        console.print(f"[bold]📦 克隆仓库: [cyan]{repo.owner}/{repo.name}[/cyan][/bold]\n")
        
        local_path = clone_repo(repo, output, branch)
        console.print(f"[green]✓ 克隆完成: {local_path}[/green]")
        
        # 获取仓库信息
        info = get_repo_info(local_path)
        console.print(f"\n[bold]📊 仓库信息:[/bold]")
        console.print(f"  分支: [cyan]{info.get('branch', 'N/A')}[/cyan]")
        console.print(f"  文件数: [cyan]{info.get('total_files', 'N/A')}[/cyan]")
        
        if 'last_commit' in info:
            commit = info['last_commit']
            console.print(f"  最新提交: [dim]{commit['message']}[/dim]")
            console.print(f"  作者: [dim]{commit['author']}[/dim]")
            console.print(f"  日期: [dim]{commit['date']}[/dim]")
        
        # 提示下一步
        console.print("\n[bold]💡 下一步操作:[/bold]")
        console.print(f"  [cyan]repomind analyze {local_path}[/cyan]  分析仓库")
        
    except Exception as e:
        console.print(f"[red]✗ 错误: {e}[/red]")


@cli.command('export-neo4j')
@click.option('--format', '-f', type=click.Choice(['cypher', 'json', 'csv']), default='cypher', help='导出格式')
@click.option('--output', '-o', help='输出路径')
@click.pass_context
def export_neo4j(ctx, format, output):
    """导出为Neo4j格式
    
    示例:
      repomind export-neo4j -f cypher -o graph.cypher
      repomind export-neo4j -f json -o graph.json
      repomind export-neo4j -f csv -o neo4j_import/
    """
    from repomind.neo4j_export import export_to_neo4j_cypher, export_to_neo4j_json, export_to_neo4j_csv
    
    kg = ctx.obj['kg']
    project = ctx.obj.get('project')
    
    if not kg.load_graph_by_name(project):
        return
    
    graph = kg.current_graph
    
    if format == 'cypher':
        if not output:
            output = f"{project or 'graph'}.cypher"
        result = export_to_neo4j_cypher(graph, output)
        console.print(f"[green]✓ Cypher脚本已导出: {output}[/green]")
    
    elif format == 'json':
        if not output:
            output = f"{project or 'graph'}_neo4j.json"
        result = export_to_neo4j_json(graph, output)
        console.print(f"[green]✓ JSON已导出: {output}[/green]")
    
    elif format == 'csv':
        if not output:
            output = "neo4j_import"
        result = export_to_neo4j_csv(graph, output)
        console.print(f"[green]✓ CSV已导出到: {output}/[/green]")
        console.print(f"  节点文件: [dim]{result['nodes_file']}[/dim]")
        console.print(f"  关系文件: [dim]{result['relationships_file']}[/dim]")
        console.print(f"  导入脚本: [dim]{result['import_script']}[/dim]")


@cli.command('git-history')
@click.option('--max-commits', '-n', default=100, help='最大提交数')
@click.option('--since', '-s', help='起始日期 (YYYY-MM-DD)')
@click.pass_context
def git_history(ctx, max_commits, since):
    """分析Git历史
    
    示例:
      repomind git-history
      repomind git-history -n 500
      repomind git-history --since 2024-01-01
    """
    from repomind.git_history import get_commit_history, get_contributors, analyze_repo_evolution, generate_contributor_graph
    
    kg = ctx.obj['kg']
    
    # 查找仓库路径
    repo_path = None
    if kg.current_path and Path(kg.current_path).exists():
        repo_path = str(kg.current_path)
    else:
        console.print("[red]✗ 请先分析一个项目[/red]")
        return
    
    console.print(f"[bold]📊 分析Git历史: [cyan]{repo_path}[/cyan][/bold]\n")
    
    # 分析演变
    evolution = analyze_repo_evolution(repo_path, max_commits)
    
    if not evolution:
        console.print("[yellow]⚠ 没有找到Git历史[/yellow]")
        return
    
    # 显示统计
    stats_table = Table(
        title="[bold]📈 Git统计[/bold]",
        box=box.ROUNDED, show_header=True, header_style="bold magenta"
    )
    stats_table.add_column("指标", style="cyan")
    stats_table.add_column("值", style="green")
    
    stats_table.add_row("总提交数", str(evolution.get('total_commits', 0)))
    stats_table.add_row("总新增行", str(evolution.get('total_insertions', 0)))
    stats_table.add_row("总删除行", str(evolution.get('total_deletions', 0)))
    stats_table.add_row("净变化", str(evolution.get('net_change', 0)))
    stats_table.add_row("首次提交", evolution.get('first_commit', 'N/A'))
    stats_table.add_row("最新提交", evolution.get('last_commit', 'N/A'))
    
    console.print(stats_table)
    
    # 显示贡献者
    contributors = get_contributors(repo_path, max_commits)
    
    if contributors:
        console.print()
        contrib_table = Table(
            title="[bold]👥 贡献者[/bold]",
            box=box.ROUNDED, show_header=True, header_style="bold cyan"
        )
        contrib_table.add_column("#", style="dim", width=4)
        contrib_table.add_column("名称", style="cyan")
        contrib_table.add_column("提交数", style="green", justify="right")
        contrib_table.add_column("新增行", style="green", justify="right")
        contrib_table.add_column("删除行", style="red", justify="right")
        
        for i, c in enumerate(contributors[:10], 1):
            contrib_table.add_row(
                str(i), c.name, str(c.commits),
                str(c.insertions), str(c.deletions)
            )
        
        console.print(contrib_table)
    
    # 生成贡献者图谱
    if contributors:
        graph_file = "contributors.md"
        generate_contributor_graph(contributors, graph_file)
        console.print(f"\n[green]✓ 贡献者图谱已生成: {graph_file}[/green]")


@cli.command()
@click.argument('plugin_name')
@click.argument('plugin_type', type=click.Choice(['extractor', 'renderer', 'exporter']))
@click.option('--output', '-o', help='输出目录')
def create_plugin(plugin_name, plugin_type, output):
    """创建插件模板
    
    示例:
      repomind create-plugin my-extractor extractor
      repomind create-plugin my-renderer renderer
    """
    from repomind.plugin_system import create_plugin_template
    
    try:
        plugin_file = create_plugin_template(plugin_name, plugin_type, output)
        console.print(f"[green]✓ 插件模板已创建: {plugin_file}[/green]")
        console.print("\n[bold]📝 下一步:[/bold]")
        console.print(f"  1. 编辑 [cyan]{plugin_file}[/cyan]")
        console.print("  2. 实现提取/渲染/导出逻辑")
        console.print("  3. 插件会自动被加载")
    except Exception as e:
        console.print(f"[red]✗ 创建失败: {e}[/red]")


@cli.command('list-plugins')
def list_plugins():
    """列出所有插件"""
    from repomind.plugin_system import get_plugin_manager
    
    manager = get_plugin_manager()
    manager.load_all_plugins()
    
    plugins = manager.list_plugins()
    
    if not plugins:
        console.print("[yellow]没有找到插件[/yellow]")
        console.print("\n[bold]💡 创建插件:[/bold]")
        console.print("  [cyan]repomind create-plugin my-plugin extractor[/cyan]")
        return
    
    table = Table(
        title="[bold]🔌 已安装插件[/bold]",
        box=box.ROUNDED, show_header=True, header_style="bold magenta"
    )
    table.add_column("名称", style="cyan")
    table.add_column("类型", style="magenta")
    table.add_column("版本", style="green")
    table.add_column("描述", style="dim")
    table.add_column("状态", style="green")
    
    for plugin in plugins:
        status = "✓ 启用" if plugin['enabled'] else "✗ 禁用"
        table.add_row(
            plugin['name'],
            plugin['type'],
            plugin['version'],
            plugin['description'],
            status
        )
    
    console.print(table)


@cli.command('parallel-analyze')
@click.argument('path')
@click.option('--workers', '-w', default=4, help='并行线程数')
@click.option('--benchmark', is_flag=True, help='运行基准测试')
@click.pass_context
def parallel_analyze(ctx, path, workers, benchmark):
    """并行分析（多线程）
    
    示例:
      repomind parallel-analyze ./my-project
      repomind parallel-analyze ./my-project -w 8
      repomind parallel-analyze ./my-project --benchmark
    """
    from repomind.parallel_extractor import extract_from_directory_parallel, benchmark_extraction
    
    if benchmark:
        console.print(f"[bold]🏃 运行基准测试...[/bold]\n")
        results = benchmark_extraction(path, [1, 2, 4, 8])
        
        table = Table(
            title="[bold]📊 基准测试结果[/bold]",
            box=box.ROUNDED, show_header=True, header_style="bold magenta"
        )
        table.add_column("线程数", style="cyan")
        table.add_column("时间(秒)", style="green")
        table.add_column("实体数", style="green")
        table.add_column("关系数", style="green")
        
        for workers, data in results.items():
            table.add_row(
                str(workers),
                str(data['time']),
                str(data['entities']),
                str(data['relations'])
            )
        
        console.print(table)
        return
    
    console.print(f"[bold]⚡ 并行分析: [cyan]{path}[/cyan] (线程数: {workers})[/bold]\n")
    
    def progress_callback(current, total):
        console.print(f"\r  进度: {current}/{total}", end='')
    
    try:
        graph, stats = extract_from_directory_parallel(path, workers, progress_callback=progress_callback)
        console.print()  # 换行
        
        console.print(f"\n[green]✓ 分析完成![/green]")
        console.print(f"  实体: [cyan]{stats['entities']}[/cyan]")
        console.print(f"  关系: [cyan]{stats['relations']}[/cyan]")
        console.print(f"  成功: [cyan]{stats['success']}[/cyan]")
        console.print(f"  失败: [red]{stats['failed']}[/red]")
        
        if stats['errors']:
            console.print(f"\n[yellow]⚠ 失败详情:[/yellow]")
            for err in stats['errors'][:5]:
                console.print(f"  - {err['file']}: {err['error']}")
        
        # 保存结果
        kg = ctx.obj['kg']
        output_name = Path(path).name
        graph_path = kg.builder.save_graph(graph, output_name)
        console.print(f"\n[green]✓ 图谱已保存: {graph_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ 错误: {e}[/red]")


def main():
    """主入口函数"""
    cli()


if __name__ == '__main__':
    main()