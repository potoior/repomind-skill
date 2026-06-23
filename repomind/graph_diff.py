"""图谱对比模块 - 比较两个知识图谱的差异"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from pydantic import BaseModel

from .models import KnowledgeGraph, Entity, Relation, EntityType, RelationType


class EntityChange(BaseModel):
    """实体变更"""
    name: str
    change_type: str  # 'added', 'deleted', 'modified'
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    old_description: Optional[str] = None
    new_description: Optional[str] = None
    old_source_file: Optional[str] = None
    new_source_file: Optional[str] = None


class RelationChange(BaseModel):
    """关系变更"""
    source: str
    target: str
    relation_type: str
    change_type: str  # 'added', 'deleted'
    description: Optional[str] = None


class GraphDiff(BaseModel):
    """图谱差异"""
    entity_changes: List[EntityChange] = []
    relation_changes: List[RelationChange] = []
    
    # 统计信息
    entities_added: int = 0
    entities_deleted: int = 0
    entities_modified: int = 0
    relations_added: int = 0
    relations_deleted: int = 0
    
    # 旧图谱和新图谱的统计
    old_entity_count: int = 0
    new_entity_count: int = 0
    old_relation_count: int = 0
    new_relation_count: int = 0


def diff_graphs(old_graph: KnowledgeGraph, new_graph: KnowledgeGraph) -> GraphDiff:
    """
    比较两个知识图谱，返回差异
    
    Args:
        old_graph: 旧的知识图谱
        new_graph: 新的知识图谱
        
    Returns:
        GraphDiff 对象，包含所有变更
    """
    diff = GraphDiff(
        old_entity_count=len(old_graph.entities),
        new_entity_count=len(new_graph.entities),
        old_relation_count=len(old_graph.relations),
        new_relation_count=len(new_graph.relations)
    )
    
    # 建立实体索引 (name+type) -> Entity
    old_entities = {}
    for e in old_graph.entities:
        key = _entity_key(e)
        old_entities[key] = e
    
    new_entities = {}
    for e in new_graph.entities:
        key = _entity_key(e)
        new_entities[key] = e
    
    # 查找新增和修改的实体
    for key, new_entity in new_entities.items():
        if key not in old_entities:
            diff.entity_changes.append(EntityChange(
                name=new_entity.name,
                change_type='added',
                new_type=new_entity.type.value,
                new_description=new_entity.description,
                new_source_file=new_entity.source_file
            ))
            diff.entities_added += 1
        else:
            old_entity = old_entities[key]
            changes = _compare_entities(old_entity, new_entity)
            if changes:
                diff.entity_changes.append(EntityChange(
                    name=new_entity.name,
                    change_type='modified',
                    old_type=old_entity.type.value,
                    new_type=new_entity.type.value,
                    old_description=old_entity.description,
                    new_description=new_entity.description,
                    old_source_file=old_entity.source_file,
                    new_source_file=new_entity.source_file
                ))
                diff.entities_modified += 1
    
    # 查找删除的实体
    for key, old_entity in old_entities.items():
        if key not in new_entities:
            diff.entity_changes.append(EntityChange(
                name=old_entity.name,
                change_type='deleted',
                old_type=old_entity.type.value,
                old_description=old_entity.description,
                old_source_file=old_entity.source_file
            ))
            diff.entities_deleted += 1
    
    # 建立关系索引 (source+target+type) -> Relation
    old_relations = {}
    for r in old_graph.relations:
        key = _relation_key(r)
        old_relations[key] = r
    
    new_relations = {}
    for r in new_graph.relations:
        key = _relation_key(r)
        new_relations[key] = r
    
    # 查找新增的关系
    for key, new_relation in new_relations.items():
        if key not in old_relations:
            diff.relation_changes.append(RelationChange(
                source=new_relation.source,
                target=new_relation.target,
                relation_type=new_relation.type.value,
                change_type='added',
                description=new_relation.description
            ))
            diff.relations_added += 1
    
    # 查找删除的关系
    for key, old_relation in old_relations.items():
        if key not in new_relations:
            diff.relation_changes.append(RelationChange(
                source=old_relation.source,
                target=old_relation.target,
                relation_type=old_relation.type.value,
                change_type='deleted',
                description=old_relation.description
            ))
            diff.relations_deleted += 1
    
    return diff


def _entity_key(entity: Entity) -> str:
    """生成实体的唯一键"""
    return f"{entity.name}|{entity.type.value}"


def _relation_key(relation: Relation) -> str:
    """生成关系的唯一键"""
    return f"{relation.source}|{relation.target}|{relation.type.value}"


def _compare_entities(old: Entity, new: Entity) -> Dict[str, Tuple]:
    """比较两个实体的差异"""
    changes = {}
    
    if old.type != new.type:
        changes['type'] = (old.type.value, new.type.value)
    
    if old.description != new.description:
        changes['description'] = (old.description, new.description)
    
    if old.source_file != new.source_file:
        changes['source_file'] = (old.source_file, new.source_file)
    
    return changes


def format_diff_summary(diff: GraphDiff) -> str:
    """格式化差异摘要"""
    lines = []
    lines.append("📊 图谱对比摘要")
    lines.append("=" * 40)
    lines.append(f"实体: {diff.old_entity_count} → {diff.new_entity_count}")
    lines.append(f"关系: {diff.old_relation_count} → {diff.new_relation_count}")
    lines.append("")
    lines.append("变更统计:")
    lines.append(f"  实体: +{diff.entities_added} -{diff.entities_deleted} ~{diff.entities_modified}")
    lines.append(f"  关系: +{diff.relations_added} -{diff.relations_deleted}")
    
    return "\n".join(lines)


def format_diff_detail(diff: GraphDiff) -> str:
    """格式化详细差异"""
    lines = []
    lines.append(format_diff_summary(diff))
    lines.append("")
    
    # 实体变更
    if diff.entity_changes:
        lines.append("📦 实体变更")
        lines.append("-" * 40)
        
        added = [c for c in diff.entity_changes if c.change_type == 'added']
        deleted = [c for c in diff.entity_changes if c.change_type == 'deleted']
        modified = [c for c in diff.entity_changes if c.change_type == 'modified']
        
        if added:
            lines.append("\n✅ 新增:")
            for c in added:
                lines.append(f"  + {c.name} ({c.new_type})")
                if c.new_description:
                    lines.append(f"    描述: {c.new_description}")
        
        if deleted:
            lines.append("\n❌ 删除:")
            for c in deleted:
                lines.append(f"  - {c.name} ({c.old_type})")
        
        if modified:
            lines.append("\n🔄 修改:")
            for c in modified:
                lines.append(f"  ~ {c.name}")
                if c.old_type != c.new_type:
                    lines.append(f"    类型: {c.old_type} → {c.new_type}")
                if c.old_description != c.new_description:
                    lines.append(f"    描述: {c.old_description or '(空)'} → {c.new_description or '(空)'}")
                if c.old_source_file != c.new_source_file:
                    lines.append(f"    来源: {c.old_source_file or '(空)'} → {c.new_source_file or '(空)'}")
    
    # 关系变更
    if diff.relation_changes:
        lines.append("")
        lines.append("🔗 关系变更")
        lines.append("-" * 40)
        
        added = [c for c in diff.relation_changes if c.change_type == 'added']
        deleted = [c for c in diff.relation_changes if c.change_type == 'deleted']
        
        if added:
            lines.append("\n✅ 新增:")
            for c in added:
                lines.append(f"  + {c.source} --[{c.relation_type}]--> {c.target}")
        
        if deleted:
            lines.append("\n❌ 删除:")
            for c in deleted:
                lines.append(f"  - {c.source} --[{c.relation_type}]--> {c.target}")
    
    if not diff.entity_changes and not diff.relation_changes:
        lines.append("")
        lines.append("✅ 没有发现差异")
    
    return "\n".join(lines)
