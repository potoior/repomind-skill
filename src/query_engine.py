from typing import List, Optional
from .models import KnowledgeGraph, Entity, Relation, EntityType, RelationType


class QueryEngine:
    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def find_entity(self, name: str) -> Optional[Entity]:
        name_lower = name.lower()
        for entity in self.graph.entities:
            if entity.name.lower() == name_lower:
                return entity
        return None

    def find_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        return [e for e in self.graph.entities if e.type == entity_type]

    def find_relations(self, entity_name: str) -> List[Relation]:
        entity_lower = entity_name.lower()
        return [
            r for r in self.graph.relations
            if r.source.lower() == entity_lower or r.target.lower() == entity_lower
        ]

    def find_dependencies(self, module_name: str) -> List[Entity]:
        dependencies = []
        for relation in self.graph.relations:
            if relation.source.lower() == module_name.lower() and relation.type == RelationType.DEPENDS_ON:
                target_entity = self.find_entity(relation.target)
                if target_entity:
                    dependencies.append(target_entity)
        return dependencies

    def find_documents(self, entity_name: str) -> List[Entity]:
        documents = []
        for relation in self.graph.relations:
            if relation.target.lower() == entity_name.lower() and relation.type == RelationType.DOCUMENTS:
                source_entity = self.find_entity(relation.source)
                if source_entity and source_entity.type == EntityType.DOCUMENT:
                    documents.append(source_entity)
        return documents

    def find_related(self, entity_name: str) -> List[Entity]:
        related = []
        for relation in self.graph.relations:
            if relation.source.lower() == entity_name.lower():
                target = self.find_entity(relation.target)
                if target:
                    related.append(target)
            elif relation.target.lower() == entity_name.lower():
                source = self.find_entity(relation.source)
                if source:
                    related.append(source)
        return related

    def search_entities(self, keyword: str) -> List[Entity]:
        keyword_lower = keyword.lower()
        return [
            e for e in self.graph.entities
            if keyword_lower in e.name.lower() or (e.description and keyword_lower in e.description.lower())
        ]