"""并行提取 - 多线程知识提取"""

import os
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from .models import Entity, Relation, KnowledgeGraph
from .knowledge_extractor import KnowledgeExtractor


@dataclass
class ExtractionResult:
    """提取结果"""
    file_path: str
    entities: List[Entity]
    relations: List[Relation]
    success: bool
    error: Optional[str] = None


def extract_single_file(
    file_path: str,
    content: str,
    is_code: bool,
    extractor: KnowledgeExtractor = None
) -> ExtractionResult:
    """
    提取单个文件的知识
    
    Args:
        file_path: 文件路径
        content: 文件内容
        is_code: 是否为代码文件
        extractor: 提取器实例
        
    Returns:
        提取结果
    """
    if extractor is None:
        extractor = KnowledgeExtractor()
    
    try:
        if is_code:
            entities, relations = extractor._extract_from_code(file_path, content)
        else:
            entities, relations = extractor._extract_from_document(file_path, content)
        
        return ExtractionResult(
            file_path=file_path,
            entities=entities,
            relations=relations,
            success=True
        )
    except Exception as e:
        return ExtractionResult(
            file_path=file_path,
            entities=[],
            relations=[],
            success=False,
            error=str(e)
        )


def extract_parallel(
    files: List[Tuple[str, str, bool]],
    max_workers: int = 4,
    progress_callback=None
) -> Tuple[List[Entity], List[Relation], Dict]:
    """
    并行提取多个文件的知识
    
    Args:
        files: [(file_path, content, is_code), ...] 列表
        max_workers: 最大线程数
        progress_callback: 进度回调函数
        
    Returns:
        (entities, relations, stats) 元组
    """
    all_entities = []
    all_relations = []
    stats = {
        'total': len(files),
        'success': 0,
        'failed': 0,
        'entities': 0,
        'relations': 0,
        'errors': []
    }
    
    # 每个线程使用独立的提取器
    def create_extractor():
        return KnowledgeExtractor()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_file = {}
        for file_path, content, is_code in files:
            extractor = create_extractor()
            future = executor.submit(extract_single_file, file_path, content, is_code, extractor)
            future_to_file[future] = file_path
        
        # 处理完成的任务
        for future in as_completed(future_to_file):
            result = future.result()
            
            if result.success:
                all_entities.extend(result.entities)
                all_relations.extend(result.relations)
                stats['success'] += 1
                stats['entities'] += len(result.entities)
                stats['relations'] += len(result.relations)
            else:
                stats['failed'] += 1
                stats['errors'].append({
                    'file': result.file_path,
                    'error': result.error
                })
            
            if progress_callback:
                progress_callback(stats['success'] + stats['failed'], stats['total'])
    
    return all_entities, all_relations, stats


def extract_from_directory_parallel(
    directory: str,
    max_workers: int = 4,
    recursive: bool = True,
    progress_callback=None
) -> Tuple[KnowledgeGraph, Dict]:
    """
    并行提取目录中的知识
    
    Args:
        directory: 目录路径
        max_workers: 最大线程数
        recursive: 是否递归
        progress_callback: 进度回调
        
    Returns:
        (KnowledgeGraph, stats) 元组
    """
    from .repository_loader import RepositoryLoader
    
    loader = RepositoryLoader()
    documents, code_files = loader.load_directory(directory, recursive)
    
    # 准备文件列表
    files = []
    
    # 文档文件
    for doc in documents:
        files.append((doc.path, doc.content, False))
    
    # 代码文件
    for file_path, content in code_files:
        files.append((file_path, content, True))
    
    # 并行提取
    entities, relations, stats = extract_parallel(files, max_workers, progress_callback)
    
    # 去重
    extractor = KnowledgeExtractor()
    entities = extractor._deduplicate(entities)
    relations = extractor._deduplicate_relations(relations)
    
    graph = KnowledgeGraph(entities=entities, relations=relations)
    
    return graph, stats


def benchmark_extraction(directory: str, workers_list: List[int] = None) -> Dict:
    """
    基准测试不同线程数的提取性能
    
    Args:
        directory: 目录路径
        workers_list: 要测试的线程数列表
        
    Returns:
        基准测试结果
    """
    import time
    
    if workers_list is None:
        workers_list = [1, 2, 4, 8]
    
    results = {}
    
    for workers in workers_list:
        start_time = time.time()
        graph, stats = extract_from_directory_parallel(directory, max_workers=workers)
        elapsed = time.time() - start_time
        
        results[workers] = {
            'time': round(elapsed, 2),
            'entities': len(graph.entities),
            'relations': len(graph.relations),
            'stats': stats
        }
    
    return results
