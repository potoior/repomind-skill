"""LLM 知识提取器 - 使用 OpenAI API 从文档和代码中提取实体关系"""

import json
import os
import urllib.request
from typing import List, Tuple, Dict, Optional

from .models import Document, Entity, Relation, EntityType, RelationType


ENTITY_TYPE_MAP = {
    "Module": EntityType.MODULE,
    "Feature": EntityType.FEATURE,
    "Document": EntityType.DOCUMENT,
    "Framework": EntityType.FRAMEWORK,
    "Database": EntityType.DATABASE,
    "Tool": EntityType.TOOL,
    "Protocol": EntityType.PROTOCOL,
    "Command": EntityType.COMMAND,
    "API": EntityType.API,
    "Service": EntityType.SERVICE,
    "Project": EntityType.PROJECT,
    "Configuration": EntityType.CONFIGURATION,
}

RELATION_TYPE_MAP = {
    "uses": RelationType.USES,
    "contains": RelationType.CONTAINS,
    "depends_on": RelationType.DEPENDS_ON,
    "extends": RelationType.EXTENDS,
    "implements": RelationType.IMPLEMENTS,
    "documents": RelationType.DOCUMENTS,
    "calls": RelationType.CALLS,
    "references": RelationType.REFERENCES,
    "belongs_to": RelationType.BELONGS_TO,
    "supports": RelationType.SUPPORTS,
    "connects_to": RelationType.CONNECTS_TO,
}

EXTRACT_SYSTEM_PROMPT = """You are a code analysis assistant. Extract entities and relations from the given content.

Respond with ONLY valid JSON in this exact format:
{
  "entities": [
    {"name": "...", "type": "Module|Feature|Document|Framework|Database|Tool|Protocol|Command|API|Service|Configuration", "description": "..."}
  ],
  "relations": [
    {"source": "...", "target": "...", "type": "uses|contains|depends_on|extends|implements|documents|calls|references"}
  ]
}

Rules:
- Entity names should be concise identifiers (class names, module names, tool names, etc.)
- Use "Module" for classes, functions, and logical units of code
- Use "Document" for documentation files
- Use "Feature" for specific capabilities or public functions
- Use "Framework", "Database", "Tool", "Protocol" for technologies mentioned
- Use "API" for API endpoints
- Use "Command" for CLI commands
- Relations should reference entity names that exist in the entities list
- Be precise: do not invent entities that are not clearly present in the content
- For code files, extract classes, public methods, imports, and inheritance
- For documents, extract modules, technologies, and API endpoints mentioned"""


class LLMExtractor:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini",
                 base_url: str = "https://api.openai.com/v1", max_tokens: int = 4096):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self._call_count = 0

    def extract_from_documents(
        self, documents: List[Document], code_files: List[Tuple[str, str]] = None
    ) -> Tuple[List[Entity], List[Relation]]:
        all_entities: List[Entity] = []
        all_relations: List[Relation] = []

        for doc in documents:
            entities, relations = self._extract_from_content(
                doc.content, doc.path, is_code=False
            )
            all_entities.extend(entities)
            all_relations.extend(relations)

        if code_files:
            for file_path, content in code_files:
                entities, relations = self._extract_from_content(
                    content, file_path, is_code=True
                )
                all_entities.extend(entities)
                all_relations.extend(relations)

        all_entities = self._deduplicate(all_entities)
        all_relations = self._deduplicate_relations(all_relations)
        return all_entities, all_relations

    def _extract_from_content(
        self, content: str, file_path: str, is_code: bool
    ) -> Tuple[List[Entity], List[Relation]]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

        truncated = content[:8000]
        file_type = "code" if is_code else "document"
        user_msg = f"Analyze this {file_type} file ({file_path}):\n\n{truncated}"

        resp = self._call_llm(EXTRACT_SYSTEM_PROMPT, user_msg)
        return self._parse_response(resp, file_path)

    def _call_llm(self, system: str, user: str) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")

        req = urllib.request.Request(
            url, data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        self._call_count += 1
        return data["choices"][0]["message"]["content"]

    def _parse_response(
        self, response: str, file_path: str
    ) -> Tuple[List[Entity], List[Relation]]:
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            return [], []

        entities = []
        for e in data.get("entities", []):
            etype = ENTITY_TYPE_MAP.get(e.get("type"))
            if etype:
                entities.append(Entity(
                    name=e["name"], type=etype,
                    description=e.get("description"), source_file=file_path,
                ))

        relations = []
        entity_names = {e.name.lower() for e in entities}
        for r in data.get("relations", []):
            rtype = RELATION_TYPE_MAP.get(r.get("type"))
            if rtype and r["source"].lower() in entity_names and r["target"].lower() in entity_names:
                relations.append(Relation(
                    source=r["source"], target=r["target"], type=rtype,
                    source_file=file_path,
                ))

        return entities, relations

    @staticmethod
    def _deduplicate(entities: List[Entity]) -> List[Entity]:
        seen = set()
        unique = []
        for e in entities:
            key = (e.name.lower(), e.type)
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique

    @staticmethod
    def _deduplicate_relations(relations: List[Relation]) -> List[Relation]:
        seen = set()
        unique = []
        for r in relations:
            key = (r.source.lower(), r.target.lower(), r.type)
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique
