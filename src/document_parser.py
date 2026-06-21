import re
from typing import List, Tuple
from .models import Document, Entity, EntityType, Relation, RelationType


class DocumentParser:
    def parse_document(self, doc: Document) -> Tuple[List[Entity], List[Relation]]:
        entities = []
        relations = []

        doc_entity = Entity(
            name=doc.title,
            type=EntityType.DOCUMENT,
            description=f"文档: {doc.path}",
            source_file=doc.path
        )
        entities.append(doc_entity)

        entities.extend(self._extract_entities_from_content(doc))
        relations.extend(self._extract_relations_from_content(doc))

        return entities, relations

    def _extract_entities_from_content(self, doc: Document) -> List[Entity]:
        entities = []
        content = doc.content.lower()

        module_patterns = [
            r"module[:\s]+(\w+)",
            r"模块[:\s]+(\w+)",
            r"##\s+(\w+)",
        ]

        for pattern in module_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) > 2:
                    entities.append(Entity(
                        name=match,
                        type=EntityType.MODULE,
                        source_file=doc.path
                    ))

        api_patterns = [
            r"api[:\s]+(\w+)",
            r"endpoint[:\s]+(\w+)",
            r"接口[:\s]+(\w+)",
        ]

        for pattern in api_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) > 2:
                    entities.append(Entity(
                        name=match,
                        type=EntityType.API,
                        source_file=doc.path
                    ))

        return entities

    def _extract_relations_from_content(self, doc: Document) -> List[Relation]:
        relations = []
        content = doc.content.lower()

        dependency_patterns = [
            r"(\w+)\s+depends\s+on\s+(\w+)",
            r"(\w+)\s+依赖\s+(\w+)",
            r"(\w+)\s+requires\s+(\w+)",
        ]

        for pattern in dependency_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for source, target in matches:
                if len(source) > 2 and len(target) > 2:
                    relations.append(Relation(
                        source=source,
                        target=target,
                        type=RelationType.DEPENDS_ON,
                        source_file=doc.path
                    ))

        support_patterns = [
            r"(\w+)\s+supports\s+(\w+)",
            r"(\w+)\s+支持\s+(\w+)",
        ]

        for pattern in support_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for source, target in matches:
                if len(source) > 2 and len(target) > 2:
                    relations.append(Relation(
                        source=source,
                        target=target,
                        type=RelationType.SUPPORTS,
                        source_file=doc.path
                    ))

        return relations