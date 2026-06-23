import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from repomind.llm_extractor import LLMExtractor, ENTITY_TYPE_MAP, RELATION_TYPE_MAP
from repomind.models import EntityType, RelationType


def test_entity_type_map_coverage():
    for name, etype in ENTITY_TYPE_MAP.items():
        assert isinstance(etype, EntityType), f"{name} not mapped to EntityType"
    assert "Module" in ENTITY_TYPE_MAP
    assert "Framework" in ENTITY_TYPE_MAP
    assert "Database" in ENTITY_TYPE_MAP


def test_relation_type_map_coverage():
    for name, rtype in RELATION_TYPE_MAP.items():
        assert isinstance(rtype, RelationType), f"{name} not mapped to RelationType"
    assert "uses" in RELATION_TYPE_MAP
    assert "depends_on" in RELATION_TYPE_MAP


def test_parse_valid_response():
    ext = LLMExtractor(api_key="test")
    response = json.dumps({
        "entities": [
            {"name": "Pipeline", "type": "Module", "description": "Data pipeline"},
            {"name": "FastAPI", "type": "Framework", "description": "Web framework"},
        ],
        "relations": [
            {"source": "Pipeline", "target": "FastAPI", "type": "uses"},
        ],
    })
    entities, relations = ext._parse_response(response, "src/pipeline.py")
    assert len(entities) == 2
    assert entities[0].name == "Pipeline"
    assert entities[0].type == EntityType.MODULE
    assert entities[1].name == "FastAPI"
    assert entities[1].type == EntityType.FRAMEWORK
    assert len(relations) == 1
    assert relations[0].source == "Pipeline"
    assert relations[0].target == "FastAPI"


def test_parse_invalid_json():
    ext = LLMExtractor(api_key="test")
    entities, relations = ext._parse_response("not json", "file.py")
    assert entities == []
    assert relations == []


def test_parse_unknown_type():
    ext = LLMExtractor(api_key="test")
    response = json.dumps({
        "entities": [{"name": "Foo", "type": "UnknownType"}],
        "relations": [],
    })
    entities, relations = ext._parse_response(response, "file.py")
    assert len(entities) == 0


def test_parse_relation_without_matching_entities():
    ext = LLMExtractor(api_key="test")
    response = json.dumps({
        "entities": [{"name": "A", "type": "Module"}],
        "relations": [{"source": "A", "target": "B", "type": "uses"}],
    })
    entities, relations = ext._parse_response(response, "file.py")
    assert len(entities) == 1
    assert len(relations) == 0


def test_deduplicate_entities():
    from repomind.models import Entity
    ext = LLMExtractor(api_key="test")
    entities = [
        Entity(name="Foo", type=EntityType.MODULE),
        Entity(name="foo", type=EntityType.MODULE),
        Entity(name="Bar", type=EntityType.MODULE),
    ]
    result = ext._deduplicate(entities)
    assert len(result) == 2


def test_deduplicate_relations():
    from repomind.models import Relation
    ext = LLMExtractor(api_key="test")
    relations = [
        Relation(source="A", target="B", type=RelationType.USES),
        Relation(source="a", target="b", type=RelationType.USES),
    ]
    result = ext._deduplicate_relations(relations)
    assert len(result) == 1


@patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False)
def test_no_api_key_raises():
    ext = LLMExtractor(api_key="")
    import pytest
    try:
        ext._extract_from_content("content", "file.py", False)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "OPENAI_API_KEY" in str(e)


@patch("src.llm_extractor.urllib.request.urlopen")
def test_call_llm(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "choices": [{"message": {"content": '{"entities": [], "relations": []}'}}]
    }).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp

    ext = LLMExtractor(api_key="test-key", model="gpt-4o-mini")
    result = ext._call_llm("system prompt", "user message")
    assert result == '{"entities": [], "relations": []}'
    assert ext._call_count == 1


if __name__ == "__main__":
    test_entity_type_map_coverage()
    test_relation_type_map_coverage()
    test_parse_valid_response()
    test_parse_invalid_json()
    test_parse_unknown_type()
    test_parse_relation_without_matching_entities()
    test_deduplicate_entities()
    test_deduplicate_relations()
    test_no_api_key_raises()
    test_call_llm()
    print("所有 llm_extractor 测试通过!")
