"""Neo4j导出 - 将知识图谱导出为Neo4j格式"""

import json
from typing import List, Dict
from pathlib import Path

from .models import KnowledgeGraph, Entity, Relation


def export_to_neo4j_cypher(graph: KnowledgeGraph, output_file: str = None) -> str:
    """
    导出为Neo4j Cypher语句
    
    Args:
        graph: 知识图谱
        output_file: 输出文件路径（可选）
        
    Returns:
        Cypher语句
    """
    lines = []
    lines.append("// Neo4j Cypher 导入脚本")
    lines.append("// 生成自 RepoMind")
    lines.append("")
    
    # 创建索引
    lines.append("// 创建索引")
    lines.append("CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.name);")
    lines.append("CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.type);")
    lines.append("")
    
    # 创建实体
    lines.append("// 创建实体")
    for entity in graph.entities:
        name = entity.name.replace("'", "\\'")
        desc = (entity.description or "").replace("'", "\\'")
        source = (entity.source_file or "").replace("'", "\\'")
        etype = entity.type.value
        
        lines.append(
            f"CREATE (n:{etype}:Entity {{name: '{name}', type: '{etype}', "
            f"description: '{desc}', source_file: '{source}'}});"
        )
    
    lines.append("")
    
    # 创建关系
    lines.append("// 创建关系")
    for rel in graph.relations:
        source = rel.source.replace("'", "\\'")
        target = rel.target.replace("'", "\\'")
        rel_type = rel.type.value.upper()
        
        lines.append(
            f"MATCH (a:Entity {{name: '{source}'}}), (b:Entity {{name: '{target}'}}) "
            f"CREATE (a)-[r:{rel_type}]->(b);"
        )
    
    cypher = "\n".join(lines)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cypher)
    
    return cypher


def export_to_neo4j_json(graph: KnowledgeGraph, output_file: str = None) -> Dict:
    """
    导出为Neo4j JSON格式（可用于neo4j-admin import）
    
    Args:
        graph: 知识图谱
        output_file: 输出文件路径（可选）
        
    Returns:
        JSON数据
    """
    # 节点数据
    nodes = []
    for i, entity in enumerate(graph.entities):
        nodes.append({
            "id": i,
            "labels": [entity.type.value, "Entity"],
            "properties": {
                "name": entity.name,
                "type": entity.type.value,
                "description": entity.description or "",
                "source_file": entity.source_file or ""
            }
        })
    
    # 建立节点索引
    node_map = {}
    for i, entity in enumerate(graph.entities):
        node_map[entity.name.lower()] = i
    
    # 关系数据
    relationships = []
    for rel in graph.relations:
        source_id = node_map.get(rel.source.lower())
        target_id = node_map.get(rel.target.lower())
        
        if source_id is not None and target_id is not None:
            relationships.append({
                "id": len(relationships),
                "type": rel.type.value.upper(),
                "startNode": source_id,
                "endNode": target_id,
                "properties": {
                    "description": rel.description or ""
                }
            })
    
    data = {
        "nodes": nodes,
        "relationships": relationships
    }
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    return data


def export_to_neo4j_csv(graph: KnowledgeGraph, output_dir: str = "neo4j_import"):
    """
    导出为Neo4j CSV格式
    
    Args:
        graph: 知识图谱
        output_dir: 输出目录
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 节点CSV
    nodes_file = output_path / "nodes.csv"
    with open(nodes_file, 'w', encoding='utf-8') as f:
        f.write("name:ID,type,description,source_file,:LABEL\n")
        for entity in graph.entities:
            name = entity.name.replace('"', '""')
            desc = (entity.description or "").replace('"', '""')
            source = (entity.source_file or "").replace('"', '""')
            f.write(f'"{name}","{entity.type.value}","{desc}","{source}","Entity;{entity.type.value}"\n')
    
    # 关系CSV
    rels_file = output_path / "relationships.csv"
    with open(rels_file, 'w', encoding='utf-8') as f:
        f.write(":START_ID,:END_ID,:TYPE\n")
        for rel in graph.relations:
            source = rel.source.replace('"', '""')
            target = rel.target.replace('"', '""')
            f.write(f'"{source}","{target}","{rel.type.value.upper()}"\n')
    
    # 生成导入脚本
    import_script = f"""#!/bin/bash
# Neo4j 导入脚本
# 生成自 RepoMind

neo4j-admin database import full \\
  --nodes=import/nodes.csv \\
  --relationships=import/relationships.csv \\
  --overwrite-destination
  
# 或者使用 Cypher Shell:
# cat import/nodes.cypher | cypher-shell -u neo4j -p password
"""
    
    script_file = output_path / "import.sh"
    with open(script_file, 'w') as f:
        f.write(import_script)
    
    return {
        "nodes_file": str(nodes_file),
        "relationships_file": str(rels_file),
        "import_script": str(script_file)
    }
