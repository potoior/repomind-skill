import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Entity, EntityType, Relation, RelationType, KnowledgeGraph, FileRecord, FileManifest
from src.knowledge_extractor import KnowledgeExtractor
from src.incremental import IncrementalAnalyzer, compute_hash


def _make_analyzer(tmp_dir: str = None):
    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp()
    extractor = KnowledgeExtractor()
    manifest_path = Path(tmp_dir) / "test.manifest.json"
    return IncrementalAnalyzer(extractor, manifest_path)


def test_compute_hash():
    h1 = compute_hash("hello")
    h2 = compute_hash("hello")
    h3 = compute_hash("world")
    assert h1 == h2
    assert h1 != h3


def test_detect_changes_empty_manifest():
    analyzer = _make_analyzer()
    manifest = FileManifest()
    current = {"a.py": "hash1", "b.py": "hash2"}
    added, modified, deleted = analyzer.detect_changes(current, manifest)
    assert set(added) == {"a.py", "b.py"}
    assert modified == []
    assert deleted == []


def test_detect_changes_no_changes():
    analyzer = _make_analyzer()
    manifest = FileManifest(files=[
        FileRecord(path="a.py", content_hash="hash1"),
        FileRecord(path="b.py", content_hash="hash2"),
    ])
    current = {"a.py": "hash1", "b.py": "hash2"}
    added, modified, deleted = analyzer.detect_changes(current, manifest)
    assert added == []
    assert modified == []
    assert deleted == []


def test_detect_changes_modified():
    analyzer = _make_analyzer()
    manifest = FileManifest(files=[
        FileRecord(path="a.py", content_hash="old"),
    ])
    current = {"a.py": "new"}
    added, modified, deleted = analyzer.detect_changes(current, manifest)
    assert added == []
    assert modified == ["a.py"]
    assert deleted == []


def test_detect_changes_deleted():
    analyzer = _make_analyzer()
    manifest = FileManifest(files=[
        FileRecord(path="a.py", content_hash="hash1"),
        FileRecord(path="b.py", content_hash="hash2"),
    ])
    current = {"a.py": "hash1"}
    added, modified, deleted = analyzer.detect_changes(current, manifest)
    assert added == []
    assert modified == []
    assert deleted == ["b.py"]


def test_detect_changes_mixed():
    analyzer = _make_analyzer()
    manifest = FileManifest(files=[
        FileRecord(path="a.py", content_hash="hash1"),
        FileRecord(path="b.py", content_hash="old"),
    ])
    current = {"a.py": "hash1", "b.py": "new", "c.py": "hash3"}
    added, modified, deleted = analyzer.detect_changes(current, manifest)
    assert added == ["c.py"]
    assert modified == ["b.py"]
    assert deleted == []


def test_remove_file_from_graph():
    analyzer = _make_analyzer()
    graph = KnowledgeGraph(
        entities=[
            Entity(name="A", type=EntityType.MODULE, source_file="a.py"),
            Entity(name="B", type=EntityType.MODULE, source_file="b.py"),
        ],
        relations=[
            Relation(source="A", target="B", type=RelationType.USES, source_file="a.py"),
        ],
    )
    result = analyzer.remove_file_from_graph(graph, "a.py")
    assert len(result.entities) == 1
    assert result.entities[0].name == "B"
    assert len(result.relations) == 0


def test_merge_new_entity():
    analyzer = _make_analyzer()
    graph = KnowledgeGraph(
        entities=[Entity(name="A", type=EntityType.MODULE)],
        relations=[],
    )
    new_entities = [Entity(name="B", type=EntityType.MODULE)]
    result = analyzer.merge(graph, new_entities, [])
    assert len(result.entities) == 2
    names = {e.name for e in result.entities}
    assert "A" in names
    assert "B" in names


def test_merge_replace_existing():
    analyzer = _make_analyzer()
    graph = KnowledgeGraph(
        entities=[Entity(name="A", type=EntityType.MODULE, description="old")],
        relations=[],
    )
    new_entities = [Entity(name="A", type=EntityType.MODULE, description="new")]
    result = analyzer.merge(graph, new_entities, [])
    assert len(result.entities) == 1
    assert result.entities[0].description == "new"


def test_merge_relations():
    analyzer = _make_analyzer()
    graph = KnowledgeGraph(entities=[], relations=[
        Relation(source="X", target="Y", type=RelationType.USES),
    ])
    new_relations = [
        Relation(source="X", target="Y", type=RelationType.USES, description="updated"),
        Relation(source="A", target="B", type=RelationType.DEPENDS_ON),
    ]
    result = analyzer.merge(graph, [], new_relations)
    assert len(result.relations) == 2


def test_save_and_load_manifest():
    tmp_dir = tempfile.mkdtemp()
    analyzer = _make_analyzer(tmp_dir)
    manifest = FileManifest(files=[
        FileRecord(path="a.py", content_hash="abc"),
    ])
    analyzer.save_manifest(manifest)
    loaded = analyzer.load_manifest()
    assert len(loaded.files) == 1
    assert loaded.files[0].path == "a.py"
    assert loaded.files[0].content_hash == "abc"


def test_extract_from_md_files():
    analyzer = _make_analyzer()
    md_files = [
        ("README.md", "# My Project\n\n## DataPipeline\n\nHandles data."),
    ]
    entities, relations = analyzer.extract_from_files({"README.md"}, md_files, [])
    names = {e.name for e in entities}
    assert "My Project" in names or "DataPipeline" in names


def test_extract_only_changed():
    analyzer = _make_analyzer()
    md_files = [
        ("README.md", "# Project"),
        ("docs/api.md", "# API\n\n## Endpoints"),
    ]
    entities, relations = analyzer.extract_from_files({"docs/api.md"}, md_files, [])
    sources = {e.source_file for e in entities if e.source_file}
    assert "docs/api.md" in sources
    assert "README.md" not in sources


if __name__ == "__main__":
    test_compute_hash()
    test_detect_changes_empty_manifest()
    test_detect_changes_no_changes()
    test_detect_changes_modified()
    test_detect_changes_deleted()
    test_detect_changes_mixed()
    test_remove_file_from_graph()
    test_merge_new_entity()
    test_merge_replace_existing()
    test_merge_relations()
    test_save_and_load_manifest()
    test_extract_from_md_files()
    test_extract_only_changed()
    print("所有 incremental 测试通过!")
