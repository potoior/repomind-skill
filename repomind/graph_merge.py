"""图谱合并模块 - 合并多个知识图谱"""

from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel

from .models import KnowledgeGraph, Entity, Relation, EntityType, RelationType


class MergeConflict(BaseModel):
    """合并冲突"""
    entity_name: str
    old_type: str
    new_type: str
    old_source: str
    new_source: str
    resolution: str = 'skip'  # 'skip', 'overwrite', 'keep_both'


class MergeResult(BaseModel):
    """合并结果"""
    merged_graph: KnowledgeGraph
    conflicts: List[MergeConflict] = []
    entities_added: int = 0
    relations_added: int = 0
    entities_skipped: int = 0
    source_projects: List[str] = []


class MergeOptions(BaseModel):
    """合并选项"""
    conflict_strategy: str = 'skip'  # 'skip', 'overwrite', 'keep_both'
    prefix_project: bool = False  # 是否在实体名前加项目前缀
    deduplicate_relations: bool = True  # 是否去重关系


def merge_graphs(
    graphs: List[Tuple[str, KnowledgeGraph]],
    options: MergeOptions = None
) -> MergeResult:
    """
    合并多个知识图谱
    
    Args:
        graphs: [(project_name, KnowledgeGraph), ...] 列表
        options: 合并选项
        
    Returns:
        MergeResult 包含合并后的图谱和统计信息
    """
    if options is None:
        options = MergeOptions()
    
    merged = KnowledgeGraph(entities=[], relations=[])
    conflicts = []
    entities_added = 0
    relations_added = 0
    entities_skipped = 0
    source_projects = []
    
    # 建立实体索引: (name, type) -> Entity
    entity_index: Dict[Tuple[str, str], Entity] = {}
    # 原始实体名到带前缀名称的映射
    name_map: Dict[str, str] = {}
    
    for project_name, graph in graphs:
        source_projects.append(project_name)
        
        # 处理实体
        for entity in graph.entities:
            # 确定实体名称
            if options.prefix_project:
                new_name = f"{project_name}.{entity.name}"
            else:
                new_name = entity.name
            
            # 更新名称映射
            if options.prefix_project:
                name_map[f"{project_name}:{entity.name}"] = new_name
            
            # 检查冲突
            key = (new_name, entity.type.value)
            if key in entity_index:
                existing = entity_index[key]
                if existing.description != entity.description or existing.source_file != entity.source_file:
                    # 存在冲突
                    conflict = MergeConflict(
                        entity_name=new_name,
                        old_type=existing.type.value,
                        new_type=entity.type.value,
                        old_source=existing.source_file or '',
                        new_source=entity.source_file or '',
                        resolution=options.conflict_strategy
                    )
                    conflicts.append(conflict)
                    
                    if options.conflict_strategy == 'skip':
                        entities_skipped += 1
                        continue
                    elif options.conflict_strategy == 'overwrite':
                        # 覆盖现有实体
                        entity_index[key] = Entity(
                            name=new_name,
                            type=entity.type,
                            description=entity.description,
                            source_file=entity.source_file
                        )
                        entities_added += 1
                    # keep_both: 保留两个实体（通过添加后缀）
                    elif options.conflict_strategy == 'keep_both':
                        # 给新实体添加来源后缀
                        new_name_with_suffix = f"{new_name} ({project_name})"
                        key_with_suffix = (new_name_with_suffix, entity.type.value)
                        entity_index[key_with_suffix] = Entity(
                            name=new_name_with_suffix,
                            type=entity.type,
                            description=entity.description,
                            source_file=entity.source_file
                        )
                        entities_added += 1
                else:
                    # 完全相同，跳过
                    entities_skipped += 1
            else:
                # 新实体
                entity_index[key] = Entity(
                    name=new_name,
                    type=entity.type,
                    description=entity.description,
                    source_file=entity.source_file
                )
                entities_added += 1
        
        # 处理关系
        for relation in graph.relations:
            # 确定源和目标名称
            if options.prefix_project:
                source_key = f"{project_name}:{relation.source}"
                target_key = f"{project_name}:{relation.target}"
                new_source = name_map.get(source_key, relation.source)
                new_target = name_map.get(target_key, relation.target)
            else:
                new_source = relation.source
                new_target = relation.target
            
            # 创建新关系
            new_relation = Relation(
                source=new_source,
                target=new_target,
                type=relation.type,
                description=relation.description,
                source_file=relation.source_file
            )
            
            # 检查重复
            if options.deduplicate_relations:
                rel_key = (new_source, new_target, relation.type.value)
                existing_rel_keys = {(r.source, r.target, r.type.value) for r in merged.relations}
                if rel_key in existing_rel_keys:
                    continue
            
            merged.relations.append(new_relation)
            relations_added += 1
    
    # 将索引中的实体添加到合并结果
    merged.entities = list(entity_index.values())
    
    return MergeResult(
        merged_graph=merged,
        conflicts=conflicts,
        entities_added=entities_added,
        relations_added=relations_added,
        entities_skipped=entities_skipped,
        source_projects=source_projects
    )


def format_merge_summary(result: MergeResult) -> str:
    """格式化合并摘要"""
    lines = []
    lines.append("📊 图谱合并摘要")
    lines.append("=" * 40)
    lines.append(f"源项目: {', '.join(result.source_projects)}")
    lines.append("")
    lines.append("合并结果:")
    lines.append(f"  实体: {len(result.merged_graph.entities)} 个 (+{result.entities_added} 新增, {result.entities_skipped} 跳过)")
    lines.append(f"  关系: {len(result.merged_graph.relations)} 个 (+{result.relations_added} 新增)")
    
    if result.conflicts:
        lines.append("")
        lines.append(f"⚠️ 冲突: {len(result.conflicts)} 个")
        for conflict in result.conflicts[:10]:
            lines.append(f"  - {conflict.entity_name}: {conflict.old_source} vs {conflict.new_source}")
        if len(result.conflicts) > 10:
            lines.append(f"  ... 还有 {len(result.conflicts) - 10} 个冲突")
    
    return "\n".join(lines)
