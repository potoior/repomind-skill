import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Document, Entity, EntityType, Relation, RelationType
from src.knowledge_extractor import KnowledgeExtractor


extractor = KnowledgeExtractor()


def test_extract_document_entity():
    doc = Document(path="README.md", title="Test Project", content="# Test Project\n\nHello world", headings=["# Test Project"])
    entities, relations = extractor._extract_from_document(doc)

    doc_entities = [e for e in entities if e.type == EntityType.DOCUMENT]
    assert len(doc_entities) == 1
    assert doc_entities[0].name == "Test Project"


def test_extract_technologies_from_doc():
    doc = Document(
        path="docs/arch.md",
        title="Architecture",
        content="# Architecture\n\nWe use FastAPI with PostgreSQL and Redis, deployed on Docker.",
        headings=["# Architecture"]
    )
    entities, relations = extractor._extract_from_document(doc)

    tech_names = {e.name for e in entities if e.type in (EntityType.FRAMEWORK, EntityType.DATABASE, EntityType.TOOL)}
    assert "fastapi" in tech_names
    assert "postgresql" in tech_names
    assert "redis" in tech_names
    assert "docker" in tech_names


def test_extract_api_endpoints_from_doc():
    doc = Document(
        path="docs/api.md",
        title="API Docs",
        content="# API\n\n- `GET /users` - List users\n- `POST /orders` - Create order",
        headings=["# API"]
    )
    entities, relations = extractor._extract_from_document(doc)

    api_entities = [e for e in entities if e.type == EntityType.API]
    paths = {e.name for e in api_entities}
    assert "/users" in paths
    assert "/orders" in paths


def test_extract_modules_from_headings():
    doc = Document(
        path="README.md",
        title="MyProject",
        content="# MyProject\n\n## DataPipeline\n\nHandles data processing.\n\n## AuthManager\n\nManages authentication.",
        headings=["# MyProject", "## DataPipeline", "## AuthManager"]
    )
    entities, relations = extractor._extract_from_document(doc)

    module_names = {e.name for e in entities if e.type == EntityType.MODULE}
    assert "DataPipeline" in module_names
    assert "AuthManager" in module_names


def test_non_module_heading_filtered():
    doc = Document(
        path="README.md",
        title="MyProject",
        content="# MyProject\n\n## 快速开始\n\nInstall with pip.\n\n## 技术栈\n\nPython, FastAPI.",
        headings=["# MyProject", "## 快速开始", "## 技术栈"]
    )
    entities, relations = extractor._extract_from_document(doc)

    module_names = {e.name for e in entities if e.type == EntityType.MODULE}
    assert "快速开始" not in module_names
    assert "技术栈" not in module_names


def test_extract_from_code():
    code = '''"""My module docstring"""

import os
import json

class MyService:
    """A service class"""
    def process(self):
        """Process data"""
        pass

def helper():
    """Helper function"""
    pass
'''
    entities, relations = extractor._extract_from_code("src/service.py", code)

    entity_names = {e.name for e in entities}
    assert "service" in entity_names  # file name
    assert "MyService" in entity_names
    assert "helper" in entity_names

    # class belongs to file
    contains = [r for r in relations if r.target == "MyService" and r.type == RelationType.CONTAINS]
    assert len(contains) == 1


def test_extract_code_inheritance():
    code = '''class Base:
    pass

class Child(Base):
    pass
'''
    entities, relations = extractor._extract_from_code("src/child.py", code)

    extends = [r for r in relations if r.type == RelationType.EXTENDS]
    assert len(extends) == 1
    assert extends[0].source == "Child"
    assert extends[0].target == "Base"


def test_deduplicate_entities():
    entities = [
        Entity(name="Foo", type=EntityType.MODULE),
        Entity(name="foo", type=EntityType.MODULE),
        Entity(name="Bar", type=EntityType.MODULE),
    ]
    result = extractor._deduplicate_entities(entities)
    assert len(result) == 2


def test_deduplicate_relations():
    relations = [
        Relation(source="A", target="B", type=RelationType.USES),
        Relation(source="a", target="b", type=RelationType.USES),
    ]
    result = extractor._deduplicate_relations(relations)
    assert len(result) == 1


def test_infer_framework_database_relation():
    entities = [
        Entity(name="FastAPI", type=EntityType.FRAMEWORK),
        Entity(name="PostgreSQL", type=EntityType.DATABASE),
    ]
    relations = []
    result = extractor._infer_relations(entities, relations)

    inferred = [r for r in result if r.type == RelationType.USES and r.source == "FastAPI" and r.target == "PostgreSQL"]
    assert len(inferred) == 1


if __name__ == "__main__":
    test_extract_document_entity()
    test_extract_technologies_from_doc()
    test_extract_api_endpoints_from_doc()
    test_extract_modules_from_headings()
    test_non_module_heading_filtered()
    test_extract_from_code()
    test_extract_code_inheritance()
    test_deduplicate_entities()
    test_deduplicate_relations()
    test_infer_framework_database_relation()
    print("所有 knowledge_extractor 测试通过!")
