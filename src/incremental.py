"""增量分析器 - 检测文件变化并增量更新知识图谱"""

import hashlib
from pathlib import Path
from typing import List, Tuple, Dict, Set

from .models import (
    Entity, Relation, KnowledgeGraph, Document,
    FileRecord, FileManifest,
)


def compute_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()


class IncrementalAnalyzer:
    def __init__(self, extractor, manifest_path: Path):
        self.extractor = extractor
        self.manifest_path = manifest_path

    def load_manifest(self) -> FileManifest:
        if not self.manifest_path.exists():
            return FileManifest()
        import json
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            return FileManifest(**json.load(f))

    def save_manifest(self, manifest: FileManifest) -> None:
        import json
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(), f, ensure_ascii=False, indent=2)

    def compute_current_files(
        self, md_files: List[Tuple[str, str]], code_files: List[Tuple[str, str]]
    ) -> Dict[str, str]:
        all_files: Dict[str, str] = {}
        for path, content in md_files:
            all_files[path] = compute_hash(content)
        for path, content in code_files:
            all_files[path] = compute_hash(content)
        return all_files

    def detect_changes(
        self, current: Dict[str, str], manifest: FileManifest
    ) -> Tuple[List[str], List[str], List[str]]:
        old_map = {r.path: r.content_hash for r in manifest.files}

        added = [p for p in current if p not in old_map]
        deleted = [p for p in old_map if p not in current]
        modified = [
            p for p in current
            if p in old_map and current[p] != old_map[p]
        ]
        return added, modified, deleted

    def remove_file_from_graph(
        self, graph: KnowledgeGraph, file_path: str
    ) -> KnowledgeGraph:
        new_entities = [
            e for e in graph.entities if e.source_file != file_path
        ]
        new_relations = [
            r for r in graph.relations if r.source_file != file_path
        ]
        return KnowledgeGraph(entities=new_entities, relations=new_relations)

    def extract_from_files(
        self,
        changed_paths: Set[str],
        md_files: List[Tuple[str, str]],
        code_files: List[Tuple[str, str]],
    ) -> Tuple[List[Entity], List[Relation]]:
        all_entities: List[Entity] = []
        all_relations: List[Relation] = []

        md_exts = {".md"}
        code_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb", ".c", ".cpp", ".h"}

        for path, content in md_files:
            if path not in changed_paths:
                continue
            suffix = Path(path).suffix.lower()
            if suffix in md_exts:
                doc = Document(
                    path=path,
                    title=self._extract_title(content, path),
                    content=content,
                    headings=self._extract_headings(content),
                )
                entities, relations = self.extractor._extract_from_document(doc)
                all_entities.extend(entities)
                all_relations.extend(relations)

        for path, content in code_files:
            if path not in changed_paths:
                continue
            suffix = Path(path).suffix.lower()
            if suffix in code_exts:
                entities, relations = self.extractor._extract_from_code(path, content)
                all_entities.extend(entities)
                all_relations.extend(relations)

        return all_entities, all_relations

    def merge(
        self,
        graph: KnowledgeGraph,
        new_entities: List[Entity],
        new_relations: List[Relation],
    ) -> KnowledgeGraph:
        entity_index: Dict[Tuple[str, str], int] = {}
        for i, e in enumerate(graph.entities):
            entity_index[(e.name.lower(), e.type.value)] = i

        entities = list(graph.entities)
        for e in new_entities:
            key = (e.name.lower(), e.type.value)
            if key in entity_index:
                entities[entity_index[key]] = e
            else:
                entity_index[key] = len(entities)
                entities.append(e)

        rel_index: Dict[Tuple[str, str, str], int] = {}
        for i, r in enumerate(graph.relations):
            rel_index[(r.source.lower(), r.target.lower(), r.type.value)] = i

        relations = list(graph.relations)
        for r in new_relations:
            key = (r.source.lower(), r.target.lower(), r.type.value)
            if key in rel_index:
                relations[rel_index[key]] = r
            else:
                rel_index[key] = len(relations)
                relations.append(r)

        return KnowledgeGraph(entities=entities, relations=relations)

    def _extract_title(self, content: str, path: str) -> str:
        for line in content.split("\n"):
            if line.startswith("# "):
                return line[2:].strip()
        return Path(path).stem

    def _extract_headings(self, content: str) -> List[str]:
        return [line.strip() for line in content.split("\n") if line.startswith("#")]
