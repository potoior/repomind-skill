"""高级搜索模块 - 支持正则、模糊匹配、多项目搜索"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

from .models import KnowledgeGraph, Entity, EntityType


@dataclass
class SearchResult:
    """搜索结果"""
    entity: Entity
    score: float  # 匹配分数 0-1
    match_type: str  # 'exact', 'contains', 'fuzzy', 'regex'
    match_field: str  # 'name', 'description'
    highlight_ranges: List[Tuple[int, int]] = None  # 高亮范围


@dataclass
class SearchOptions:
    """搜索选项"""
    query: str
    entity_types: List[str] = None  # 过滤实体类型
    case_sensitive: bool = False
    use_regex: bool = False
    fuzzy: bool = False
    fuzzy_threshold: float = 0.6  # 模糊匹配阈值
    search_fields: List[str] = None  # 'name', 'description'
    max_results: int = 50
    include_relations: bool = False  # 是否包含关联实体


def search_entities(graph: KnowledgeGraph, options: SearchOptions) -> List[SearchResult]:
    """
    高级搜索实体
    
    Args:
        graph: 知识图谱
        options: 搜索选项
        
    Returns:
        搜索结果列表，按匹配分数排序
    """
    results = []
    
    if options.search_fields is None:
        options.search_fields = ['name', 'description']
    
    for entity in graph.entities:
        # 过滤实体类型
        if options.entity_types and entity.type.value not in options.entity_types:
            continue
        
        # 搜索名称
        if 'name' in options.search_fields:
            score, match_type, highlights = _match_text(
                entity.name, options.query,
                options.case_sensitive, options.use_regex, options.fuzzy, options.fuzzy_threshold
            )
            if score > 0:
                results.append(SearchResult(
                    entity=entity,
                    score=score * 1.2,  # 名称匹配权重更高
                    match_type=match_type,
                    match_field='name',
                    highlight_ranges=highlights
                ))
        
        # 搜索描述
        if 'description' in options.search_fields and entity.description:
            score, match_type, highlights = _match_text(
                entity.description, options.query,
                options.case_sensitive, options.use_regex, options.fuzzy, options.fuzzy_threshold
            )
            if score > 0:
                results.append(SearchResult(
                    entity=entity,
                    score=score,
                    match_type=match_type,
                    match_field='description',
                    highlight_ranges=highlights
                ))
    
    # 去重（同一实体只保留最高分）
    deduplicated = {}
    for result in results:
        key = (result.entity.name, result.entity.type.value)
        if key not in deduplicated or result.score > deduplicated[key].score:
            deduplicated[key] = result
    
    results = list(deduplicated.values())
    
    # 按分数排序
    results.sort(key=lambda r: r.score, reverse=True)
    
    return results[:options.max_results]


def _match_text(text: str, query: str, case_sensitive: bool, use_regex: bool, 
                fuzzy: bool, fuzzy_threshold: float) -> Tuple[float, str, List[Tuple[int, int]]]:
    """
    匹配文本
    
    Returns:
        (score, match_type, highlight_ranges) 或 (0, '', [])
    """
    if not text or not query:
        return 0, '', []
    
    text_to_check = text if case_sensitive else text.lower()
    query_to_check = query if case_sensitive else query.lower()
    
    # 精确匹配
    if text_to_check == query_to_check:
        return 1.0, 'exact', [(0, len(text))]
    
    # 正则匹配
    if use_regex:
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(query, flags)
            match = pattern.search(text)
            if match:
                return 0.9, 'regex', [(match.start(), match.end())]
        except re.error:
            pass
    
    # 包含匹配
    if query_to_check in text_to_check:
        start = text_to_check.index(query_to_check)
        end = start + len(query_to_check)
        return 0.8, 'contains', [(start, end)]
    
    # 模糊匹配
    if fuzzy:
        ratio = SequenceMatcher(None, query_to_check, text_to_check).ratio()
        if ratio >= fuzzy_threshold:
            return ratio * 0.7, 'fuzzy', []
    
    return 0, '', []


def search_with_context(graph: KnowledgeGraph, entity_name: str) -> Dict:
    """
    搜索实体并返回上下文（关联实体、关系）
    
    Args:
        graph: 知识图谱
        entity_name: 实体名称
        
    Returns:
        包含实体和关联信息的字典
    """
    from .query_engine import QueryEngine
    
    qe = QueryEngine(graph)
    entity = qe.find_entity(entity_name)
    
    if not entity:
        return None
    
    # 获取关联实体
    related = qe.find_related(entity.name)
    relations = qe.find_relations(entity.name)
    
    # 构建关系图
    outgoing = []
    incoming = []
    for r in relations:
        if r.source.lower() == entity.name.lower():
            target = qe.find_entity(r.target)
            if target:
                outgoing.append({
                    'relation': r.type.value,
                    'entity': target.name,
                    'type': target.type.value,
                    'description': target.description
                })
        else:
            source = qe.find_entity(r.source)
            if source:
                incoming.append({
                    'relation': r.type.value,
                    'entity': source.name,
                    'type': source.type.value,
                    'description': source.description
                })
    
    return {
        'entity': {
            'name': entity.name,
            'type': entity.type.value,
            'description': entity.description,
            'source_file': entity.source_file
        },
        'outgoing': outgoing,
        'incoming': incoming,
        'related_count': len(related)
    }


def search_multi_project(graphs: Dict[str, KnowledgeGraph], options: SearchOptions) -> Dict[str, List[SearchResult]]:
    """
    跨项目搜索
    
    Args:
        graphs: {project_name: KnowledgeGraph} 字典
        options: 搜索选项
        
    Returns:
        {project_name: [SearchResult]} 字典
    """
    results = {}
    
    for project_name, graph in graphs.items():
        project_results = search_entities(graph, options)
        if project_results:
            results[project_name] = project_results
    
    return results


def format_search_results(results: List[SearchResult], query: str) -> str:
    """格式化搜索结果"""
    if not results:
        return f"没有找到包含 '{query}' 的实体"
    
    lines = []
    lines.append(f"🔍 搜索结果: '{query}'")
    lines.append(f"找到 {len(results)} 个匹配")
    lines.append("")
    
    for i, result in enumerate(results, 1):
        entity = result.entity
        icon = _get_type_icon(entity.type.value)
        
        lines.append(f"{i}. {icon} {entity.name}")
        lines.append(f"   类型: {entity.type.value}")
        
        if entity.description:
            # 高亮匹配部分
            desc = entity.description
            if result.match_field == 'description' and result.highlight_ranges:
                desc = _highlight_text(desc, result.highlight_ranges)
            lines.append(f"   描述: {desc}")
        
        if entity.source_file:
            lines.append(f"   来源: {entity.source_file}")
        
        lines.append(f"   匹配: {result.match_type} (分数: {result.score:.2f})")
        lines.append("")
    
    return "\n".join(lines)


def _highlight_text(text: str, ranges: List[Tuple[int, int]]) -> str:
    """高亮文本中的指定范围"""
    if not ranges:
        return text
    
    result = []
    last_end = 0
    
    for start, end in sorted(ranges):
        result.append(text[last_end:start])
        result.append(f"[{text[start:end]}]")
        last_end = end
    
    result.append(text[last_end:])
    return "".join(result)


def _get_type_icon(entity_type: str) -> str:
    """获取实体类型图标"""
    icons = {
        "Project": "🎯",
        "Module": "📦",
        "Service": "⚡",
        "Protocol": "🔌",
        "Skill": "🛠️",
        "Framework": "🔧",
        "Database": "🗄️",
        "Tool": "🔨",
        "API": "🌐",
        "Configuration": "⚙️",
        "Command": "💻",
        "Feature": "✨",
        "Document": "📄"
    }
    return icons.get(entity_type, "•")
