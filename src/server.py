"""RepoMind daemon server - 常驻进程，消除重复启动开销"""

import json
import sys
import signal
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class RepoMindHandler(BaseHTTPRequestHandler):
    kg = None

    def log_message(self, format, *args):
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_stream(self, events):
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        for event in events:
            line = json.dumps(event, ensure_ascii=False) + "\n"
            chunk = f"{len(line):x}\r\n{line}\r\n"
            self.wfile.write(chunk.encode("utf-8"))
            self.wfile.flush()
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            req = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON"}, 400)
            return

        cmd = req.get("command", "")
        args = req.get("args", {})

        if cmd == "analyze":
            try:
                self._send_stream(self._stream_analyze(args))
            except Exception as e:
                self._send_stream([{"event": "error", "error": str(e)}])
            return

        handler = getattr(self, f"cmd_{cmd}", None)
        if handler is None:
            self._send_json({"error": f"unknown command: {cmd}"}, 400)
            return

        try:
            result = handler(args)
            self._send_json({"ok": True, "result": result})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _stream_analyze(self, args):
        path = args.get("path", "")
        incremental = args.get("incremental", False)
        recursive = args.get("recursive", True)
        use_llm = args.get("llm", False)
        model = args.get("model", "gpt-4o-mini")
        api_key = args.get("api_key")
        p = Path(path)

        if not p.exists():
            yield {"event": "error", "error": f"path not found: {path}"}
            return

        yield {"event": "step", "step": "scan", "status": "start"}

        ignore_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build', 'output'}
        md_exts = {'.md'}
        code_exts = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.rb', '.c', '.cpp', '.h'}

        md_files = []
        code_files = []
        if recursive:
            for root, dirs, filenames in os.walk(p):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                for f in filenames:
                    fp = Path(root) / f
                    suffix = fp.suffix.lower()
                    if suffix in md_exts:
                        md_files.append(fp)
                    elif suffix in code_exts:
                        code_files.append(fp)
        else:
            for f in p.iterdir():
                if f.suffix.lower() in md_exts:
                    md_files.append(f)
                elif f.suffix.lower() in code_exts:
                    code_files.append(f)

        yield {"event": "step", "step": "scan", "status": "done",
               "md_count": len(md_files), "code_count": len(code_files)}

        yield {"event": "step", "step": "read", "status": "start", "total": len(md_files) + len(code_files)}

        def read_file(fp):
            for enc in ['utf-8', 'utf-8-sig', 'utf-16', 'latin-1', 'gbk']:
                try:
                    return fp.read_text(encoding=enc)
                except (UnicodeDecodeError, UnicodeError):
                    continue
            return None

        md_data = []
        code_data = []
        for fp in md_files:
            content = read_file(fp)
            if content is not None:
                rel = str(fp.relative_to(p))
                md_data.append((rel, content))
            yield {"event": "progress", "step": "read", "current": len(md_data) + len(code_data)}

        for fp in code_files:
            content = read_file(fp)
            if content is not None:
                rel = str(fp.relative_to(p))
                code_data.append((rel, content))
            yield {"event": "progress", "step": "read", "current": len(md_data) + len(code_data)}

        yield {"event": "step", "step": "read", "status": "done"}

        llm_opts = {"use_llm": use_llm, "model": model, "api_key": api_key}

        if incremental:
            yield from self._do_incremental(p, md_data, code_data, llm_opts)
        else:
            yield from self._do_full(p, md_data, code_data, llm_opts)

    def _do_full(self, p, md_data, code_data, llm_opts=None):
        yield {"event": "step", "step": "extract", "status": "start"}

        from src.models import Document
        documents = []
        for rel, content in md_data:
            title = "Untitled"
            for line in content.split("\n"):
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            headings = [l.strip() for l in content.split("\n") if l.startswith("#")]
            documents.append(Document(path=rel, title=title, content=content, headings=headings))

        if llm_opts and llm_opts.get("use_llm"):
            from src.llm_extractor import LLMExtractor
            extractor = LLMExtractor(
                api_key=llm_opts.get("api_key"),
                model=llm_opts.get("model", "gpt-4o-mini"),
            )
        else:
            extractor = self.kg.extractor

        entities, relations = extractor.extract_from_documents(documents, code_data)
        yield {"event": "step", "step": "extract", "status": "done",
               "entity_count": len(entities), "relation_count": len(relations)}

        yield {"event": "step", "step": "build", "status": "start"}
        repo_name = p.name
        self.kg.project_name = repo_name
        graph = self.kg.builder.build_graph(entities, relations, repo_name)
        self.kg.current_graph = graph
        self.kg.qa_engine = self.kg._make_qa(graph)
        html_path = self.kg.builder.generate_html_visualization(graph, repo_name)
        yield {"event": "step", "step": "build", "status": "done"}

        yield {"event": "result", "data": {
            "name": repo_name, "entities": len(entities), "relations": len(relations),
            "graph_path": str(self.kg.output_dir / f"{repo_name}.graph.json"),
            "html_path": html_path,
        }}

    def _do_incremental(self, p, md_data, code_data, llm_opts=None):
        from src.incremental import IncrementalAnalyzer
        from src.models import FileRecord, FileManifest, KnowledgeGraph

        if llm_opts and llm_opts.get("use_llm"):
            from src.llm_extractor import LLMExtractor
            extractor = LLMExtractor(
                api_key=llm_opts.get("api_key"),
                model=llm_opts.get("model", "gpt-4o-mini"),
            )
        else:
            extractor = self.kg.extractor

        repo_name = p.name
        self.kg.project_name = repo_name
        manifest_path = self.kg.output_dir / f"{repo_name}.manifest.json"
        incremental = IncrementalAnalyzer(extractor, manifest_path)

        yield {"event": "step", "step": "diff", "status": "start"}
        current = incremental.compute_current_files(md_data, code_data)
        manifest = incremental.load_manifest()
        added, modified, deleted = incremental.detect_changes(current, manifest)
        yield {"event": "step", "step": "diff", "status": "done",
               "added": len(added), "modified": len(modified), "deleted": len(deleted)}

        if not added and not modified and not deleted:
            yield {"event": "result", "data": {"no_change": True, "name": repo_name}}
            return

        changed = set(added + modified)
        yield {"event": "step", "step": "extract", "status": "start"}
        new_entities, new_relations = incremental.extract_from_files(changed, md_data, code_data)
        yield {"event": "step", "step": "extract", "status": "done",
               "entity_count": len(new_entities), "relation_count": len(new_relations)}

        yield {"event": "step", "step": "merge", "status": "start"}
        try:
            graph = self.kg.builder.load_graph(repo_name)
        except FileNotFoundError:
            graph = KnowledgeGraph()

        for fp in deleted:
            graph = incremental.remove_file_from_graph(graph, fp)
        graph = incremental.merge(graph, new_entities, new_relations)

        output_file = self.kg.output_dir / f"{repo_name}.graph.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(graph.model_dump(), f, ensure_ascii=False, indent=2)
        html_path = self.kg.builder.generate_html_visualization(graph, repo_name)

        existing = {r.path: r for r in manifest.files}
        for path, h in current.items():
            existing[path] = FileRecord(path=path, content_hash=h)
        for fp in deleted:
            existing.pop(fp, None)
        incremental.save_manifest(FileManifest(files=list(existing.values())))

        self.kg.current_graph = graph
        self.kg.qa_engine = self.kg._make_qa(graph)
        yield {"event": "step", "step": "merge", "status": "done"}

        yield {"event": "result", "data": {
            "name": repo_name, "added": len(added), "modified": len(modified), "deleted": len(deleted),
            "entities": len(graph.entities), "relations": len(graph.relations),
        }}

    def cmd_ping(self, args):
        return "pong"

    def cmd_summary(self, args):
        project = args.get("project")
        if not self.kg.load_graph_by_name(project):
            return {"error": "no project loaded"}
        graph = self.kg.current_graph
        entity_types = {}
        for e in graph.entities:
            entity_types[e.type.value] = entity_types.get(e.type.value, 0) + 1
        modules = [e.name for e in graph.entities if e.type.value == "Module"]
        return {
            "project": self.kg.project_name,
            "entities": len(graph.entities),
            "relations": len(graph.relations),
            "types": entity_types,
            "modules": modules[:15],
        }

    def cmd_query(self, args):
        question = args.get("question", "")
        project = args.get("project")
        if not self.kg.load_graph_by_name(project):
            return {"error": "no project loaded"}
        return {"answer": self.kg.query(question)}

    def cmd_search(self, args):
        keyword = args.get("keyword", "")
        project = args.get("project")
        if not self.kg.load_graph_by_name(project):
            return {"error": "no project loaded"}
        results = []
        kw = keyword.lower()
        for e in self.kg.current_graph.entities:
            if kw in e.name.lower() or (e.description and kw in e.description.lower()):
                results.append({"name": e.name, "type": e.type.value, "description": e.description or ""})
        return {"results": results[:20]}

    def cmd_entity(self, args):
        name = args.get("name", "")
        project = args.get("project")
        if not self.kg.load_graph_by_name(project):
            return {"error": "no project loaded"}
        for e in self.kg.current_graph.entities:
            if e.name.lower() == name.lower():
                related = []
                for r in self.kg.current_graph.relations:
                    if r.source.lower() == name.lower():
                        related.append({"direction": "out", "type": r.type.value, "target": r.target})
                    elif r.target.lower() == name.lower():
                        related.append({"direction": "in", "type": r.type.value, "source": r.source})
                return {
                    "name": e.name, "type": e.type.value,
                    "description": e.description or "", "source_file": e.source_file or "",
                    "relations": related,
                }
        return {"error": f"entity not found: {name}"}

    def cmd_deps(self, args):
        name = args.get("name", "")
        project = args.get("project")
        if not self.kg.load_graph_by_name(project):
            return {"error": "no project loaded"}
        deps_out, deps_in = [], []
        for r in self.kg.current_graph.relations:
            if r.type.value in ("depends_on", "uses"):
                if r.source.lower() == name.lower():
                    deps_out.append(r.target)
                elif r.target.lower() == name.lower():
                    deps_in.append(r.source)
        return {"name": name, "dependencies": deps_out, "dependents": deps_in}

    def cmd_list(self, args):
        return {"graphs": self.kg.list_graphs()}

    def cmd_load(self, args):
        name = args.get("name", "")
        ok = self.kg.load_graph(name)
        if ok:
            return {"loaded": name}
        return {"error": f"project not found: {name}"}

    def cmd_export(self, args):
        fmt = args.get("format", "json")
        output = args.get("output")
        project = args.get("project")
        if not self.kg.load_graph_by_name(project):
            return {"error": "no project loaded"}
        path = self.kg.export(fmt, output)
        return {"exported": path}

    def cmd_stop(self, args):
        import threading
        threading.Thread(target=lambda: sys.exit(0), daemon=True).start()
        return {"message": "shutting down"}


def run_server(output_dir="output", host="127.0.0.1", port=19832):
    from cli import KnowledgeGraphCLI

    handler = RepoMindHandler
    handler.kg = KnowledgeGraphCLI(output_dir)

    server = HTTPServer((host, port), handler)
    print(f"RepoMind daemon listening on {host}:{port}")
    print(f"PID: {os.getpid()}")

    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("Daemon stopped.")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", "-p", type=int, default=19832)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--output", "-o", default="output")
    args = p.parse_args()
    run_server(args.output, args.host, args.port)
