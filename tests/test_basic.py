import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from repomind.models import Entity, EntityType, Relation, RelationType, KnowledgeGraph
from repomind.query_engine import QueryEngine


def test_query_engine():
    entities = [
        Entity(name="TestProject", type=EntityType.PROJECT),
        Entity(name="ModuleA", type=EntityType.MODULE),
        Entity(name="ModuleB", type=EntityType.MODULE),
        Entity(name="README", type=EntityType.DOCUMENT),
    ]

    relations = [
        Relation(source="TestProject", target="ModuleA", type=RelationType.CONTAINS),
        Relation(source="TestProject", target="ModuleB", type=RelationType.CONTAINS),
        Relation(source="ModuleA", target="ModuleB", type=RelationType.DEPENDS_ON),
    ]

    graph = KnowledgeGraph(entities=entities, relations=relations)
    engine = QueryEngine(graph)

    entity = engine.find_entity("ModuleA")
    assert entity is not None
    assert entity.name == "ModuleA"

    deps = engine.find_dependencies("ModuleA")
    assert len(deps) == 1
    assert deps[0].name == "ModuleB"

    related = engine.find_related("ModuleA")
    assert len(related) == 2

    modules = engine.find_entities_by_type(EntityType.MODULE)
    assert len(modules) == 2

    print("所有测试通过!")


if __name__ == "__main__":
    test_query_engine()