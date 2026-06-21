from typing import List
from .models import KnowledgeGraph, Entity, EntityType
from .query_engine import QueryEngine


class QAEngine:
    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
        self.query_engine = QueryEngine(graph)

    def answer_question(self, question: str) -> str:
        question_lower = question.lower()

        if any(word in question for word in ["是什么", "what is", "介绍", "explain"]):
            return self._answer_what_is(question)

        if any(word in question for word in ["依赖", "depend", "需要", "require"]):
            return self._answer_dependencies(question)

        if any(word in question for word in ["模块", "module", "组件", "component"]):
            return self._answer_modules(question)

        if any(word in question for word in ["文档", "document", "doc"]):
            return self._answer_documents(question)

        if any(word in question for word in ["技术栈", "tech", "technology", "框架", "framework"]):
            return self._answer_tech_stack(question)

        if any(word in question for word in ["数据库", "database", "db"]):
            return self._answer_databases(question)

        if any(word in question for word in ["工具", "tool"]):
            return self._answer_tools(question)

        return self._answer_general(question)

    def _answer_what_is(self, question: str) -> str:
        for entity in self.graph.entities:
            if entity.name.lower() in question.lower():
                related = self.query_engine.find_related(entity.name)
                related_names = [r.name for r in related[:5]]

                response = f"{entity.name} 是项目中的 {entity.type.value}。"
                if entity.description:
                    response += f"\n描述: {entity.description}"
                if related_names:
                    response += f"\n相关实体: {', '.join(related_names)}"
                return response

        return "抱歉，我找不到相关的实体信息。"

    def _answer_dependencies(self, question: str) -> str:
        for entity in self.graph.entities:
            if entity.name.lower() in question.lower():
                deps = self.query_engine.find_dependencies(entity.name)
                if deps:
                    dep_names = [d.name for d in deps]
                    return f"{entity.name} 依赖于: {', '.join(dep_names)}"
                else:
                    return f"{entity.name} 没有发现依赖关系。"

        return "抱歉，我找不到相关的依赖信息。"

    def _answer_modules(self, question: str) -> str:
        modules = self.query_engine.find_entities_by_type(EntityType.MODULE)
        if modules:
            module_names = [m.name for m in modules[:15]]
            return f"项目包含以下模块:\n" + "\n".join(f"  - {name}" for name in module_names)
        return "项目中没有发现模块信息。"

    def _answer_documents(self, question: str) -> str:
        documents = self.query_engine.find_entities_by_type(EntityType.DOCUMENT)
        if documents:
            doc_names = [d.name for d in documents]
            return f"项目包含以下文档:\n" + "\n".join(f"  - {name}" for name in doc_names)
        return "项目中没有发现文档信息。"

    def _answer_tech_stack(self, question: str) -> str:
        frameworks = self.query_engine.find_entities_by_type(EntityType.FRAMEWORK)
        result = "项目技术栈:\n"

        if frameworks:
            result += "\n框架:\n" + "\n".join(f"  - {f.name}" for f in frameworks)

        return result

    def _answer_databases(self, question: str) -> str:
        databases = self.query_engine.find_entities_by_type(EntityType.DATABASE)
        if databases:
            return "项目使用的数据库:\n" + "\n".join(f"  - {d.name}" for d in databases)
        return "项目中没有发现数据库信息。"

    def _answer_tools(self, question: str) -> str:
        tools = self.query_engine.find_entities_by_type(EntityType.TOOL)
        if tools:
            return "项目使用的工具:\n" + "\n".join(f"  - {t.name}" for t in tools)
        return "项目中没有发现工具信息。"

    def _answer_general(self, question: str) -> str:
        entities = self.query_engine.search_entities(question)
        if entities:
            result = "找到相关实体:\n"
            for e in entities[:5]:
                result += f"  - {e.name} ({e.type.value})"
                if e.source_file:
                    result += f" [来源: {e.source_file}]"
                result += "\n"
            return result

        return "抱歉，我无法回答这个问题。请尝试更具体的问题，例如:\n  - 有哪些模块?\n  - 技术栈是什么?\n  - 使用了哪些数据库?"