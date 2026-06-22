from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class EntityType(str, Enum):
    PROJECT = "Project"
    MODULE = "Module"
    SERVICE = "Service"
    PROTOCOL = "Protocol"
    SKILL = "Skill"
    FRAMEWORK = "Framework"
    DATABASE = "Database"
    TOOL = "Tool"
    API = "API"
    CONFIGURATION = "Configuration"
    COMMAND = "Command"
    FEATURE = "Feature"
    DOCUMENT = "Document"


class RelationType(str, Enum):
    DEPENDS_ON = "depends_on"
    SUPPORTS = "supports"
    USES = "uses"
    CONTAINS = "contains"
    IMPLEMENTS = "implements"
    EXTENDS = "extends"
    CONNECTS_TO = "connects_to"
    CALLS = "calls"
    REFERENCES = "references"
    DOCUMENTS = "documents"
    BELONGS_TO = "belongs_to"


class Entity(BaseModel):
    name: str
    type: EntityType
    description: Optional[str] = None
    source_file: Optional[str] = None


class Relation(BaseModel):
    source: str
    target: str
    type: RelationType
    description: Optional[str] = None
    source_file: Optional[str] = None


class Document(BaseModel):
    path: str
    title: str
    content: str
    headings: List[str] = []


class KnowledgeGraph(BaseModel):
    entities: List[Entity] = []
    relations: List[Relation] = []


class FileRecord(BaseModel):
    path: str
    content_hash: str


class FileManifest(BaseModel):
    files: List[FileRecord] = []


class RepositoryContext(BaseModel):
    repo_url: str
    repo_name: str
    local_path: str
    documents: List[Document] = []