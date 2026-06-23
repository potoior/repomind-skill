import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from repomind.models import Entity, EntityType, Relation, RelationType, KnowledgeGraph
from repomind.qa_engine import QAEngine


def _make_engine():
    entities = [
        Entity(name="Pipeline", type=EntityType.MODULE, description="Data pipeline module"),
        Entity(name="Transform", type=EntityType.MODULE),
        Entity(name="Redis", type=EntityType.DATABASE),
        Entity(name="FastAPI", type=EntityType.FRAMEWORK),
        Entity(name="a", type=EntityType.MODULE),
    ]
    relations = [
        Relation(source="Pipeline", target="Transform", type=RelationType.DEPENDS_ON),
        Relation(source="Pipeline", target="Redis", type=RelationType.USES),
    ]
    graph = KnowledgeGraph(entities=entities, relations=relations)
    return QAEngine(graph)


def test_what_is_matches_long_name():
    engine = _make_engine()
    answer = engine.answer_question("Pipeline是什么")
    assert "Pipeline" in answer
    assert "Module" in answer


def test_what_is_ignores_short_name():
    engine = _make_engine()
    answer = engine.answer_question("请介绍一下这个项目")
    assert "抱歉" in answer


def test_what_is_prefers_longer_match():
    engine = _make_engine()
    answer = engine.answer_question("Transform是什么")
    assert "Transform" in answer


def test_dependencies_query():
    engine = _make_engine()
    answer = engine.answer_question("Pipeline依赖什么")
    assert "Transform" in answer


def test_dependencies_no_match_for_short_name():
    engine = _make_engine()
    answer = engine.answer_question("这个项目依赖什么")
    assert "抱歉" in answer


def test_modules_query():
    engine = _make_engine()
    answer = engine.answer_question("有哪些模块")
    assert "Pipeline" in answer


def test_tech_stack_query():
    engine = _make_engine()
    answer = engine.answer_question("技术栈是什么")
    assert "FastAPI" in answer


def test_databases_query():
    engine = _make_engine()
    answer = engine.answer_question("使用了哪些数据库")
    assert "Redis" in answer


if __name__ == "__main__":
    test_what_is_matches_long_name()
    test_what_is_ignores_short_name()
    test_what_is_prefers_longer_match()
    test_dependencies_query()
    test_dependencies_no_match_for_short_name()
    test_modules_query()
    test_tech_stack_query()
    test_databases_query()
    print("所有 qa_engine 测试通过!")
