#!/usr/bin/env python3
"""生成项目合规性分析报告"""

import sys
import io
import json
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def load_graph(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_compliance(graph: dict) -> dict:
    """分析项目合规性"""
    issues = []
    warnings = []
    suggestions = []
    
    entities = graph['entities']
    relations = graph['relations']
    
    # 1. 检查文档完整性
    documents = [e for e in entities if e['type'] == 'Document']
    doc_paths = [d.get('source_file', '').lower() for d in documents]
    doc_names = [d['name'].lower() for d in documents]
    
    required_docs = {
        'README': ['readme'],
        'LICENSE': ['license'],
        'CONTRIBUTING': ['contributing'],
        'CHANGELOG': ['changelog']
    }
    
    for doc_key, keywords in required_docs.items():
        # 检查文件路径
        found_by_path = any(any(kw in path for kw in keywords) for path in doc_paths)
        # 检查文档名称
        found_by_name = any(any(kw in name for kw in keywords) for name in doc_names)
        
        if not found_by_path and not found_by_name:
            issues.append(f"缺少必要文档: {doc_key}")
    
    # 2. 检查模块描述
    modules = [e for e in entities if e['type'] == 'Module']
    modules_without_desc = [m for m in modules if not m.get('description')]
    if modules_without_desc:
        warnings.append(f"{len(modules_without_desc)} 个模块缺少描述")
        for m in modules_without_desc[:5]:
            warnings.append(f"  - {m['name']}")
    
    # 3. 检查命名规范
    for entity in entities:
        name = entity['name']
        # 检查是否包含空格
        if ' ' in name and entity['type'] in ['Module', 'Feature']:
            warnings.append(f"命名包含空格: {name} (建议使用驼峰或下划线)")
    
    # 4. 检查孤立实体 (排除Command和Document类型)
    connected_entities = set()
    for r in relations:
        connected_entities.add(r['source'].lower())
        connected_entities.add(r['target'].lower())
    
    # Command和Document类型通常不需要直接关联
    ignore_types = {'Command', 'Document'}
    orphaned = [e for e in entities if e['name'].lower() not in connected_entities and e['type'] not in ignore_types]
    if orphaned:
        warnings.append(f"{len(orphaned)} 个孤立实体 (无关联关系)")
        for o in orphaned[:5]:
            warnings.append(f"  - {o['name']} ({o['type']})")
    
    # 5. 检查循环依赖
    deps = {}
    for r in relations:
        if r['type'] == 'depends_on':
            if r['source'] not in deps:
                deps[r['source']] = []
            deps[r['source']].append(r['target'])
    
    # 6. 检查技术栈一致性
    databases = [e for e in entities if e['type'] == 'Database']
    if len(databases) > 3:
        suggestions.append(f"使用了 {len(databases)} 种数据库，考虑减少技术栈复杂度")
    
    # 7. 检查文档覆盖
    doc_relations = [r for r in relations if r['type'] == 'documents']
    documented_modules = set(r['target'] for r in doc_relations)
    undocumented = [m for m in modules if m['name'] not in documented_modules]
    if undocumented:
        warnings.append(f"{len(undocumented)} 个模块缺少文档引用")
        for m in undocumented[:5]:
            warnings.append(f"  - {m['name']}")
    
    # 8. 检查代码文件
    code_files = set()
    for e in entities:
        if e.get('source_file') and not e['source_file'].endswith('.md'):
            code_files.add(e['source_file'])
    
    if len(code_files) < 3:
        suggestions.append("代码文件较少，考虑添加更多示例代码")
    
    return {
        'issues': issues,
        'warnings': warnings,
        'suggestions': suggestions,
        'stats': {
            'total_entities': len(entities),
            'total_relations': len(relations),
            'documents': len(documents),
            'modules': len(modules),
            'code_files': len(code_files),
            'orphaned_entities': len(orphaned),
            'undocumented_modules': len(undocumented)
        }
    }


def generate_report(project_name: str, analysis: dict):
    """生成报告"""
    report = f"""
{'='*60}
项目合规性分析报告
{'='*60}

项目名称: {project_name}
分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*60}
📊 统计概览
{'='*60}

  实体总数:       {analysis['stats']['total_entities']}
  关系总数:       {analysis['stats']['total_relations']}
  文档数量:       {analysis['stats']['documents']}
  模块数量:       {analysis['stats']['modules']}
  代码文件:       {analysis['stats']['code_files']}
  孤立实体:       {analysis['stats']['orphaned_entities']}
  未文档化模块:   {analysis['stats']['undocumented_modules']}

{'='*60}
❌ 严重问题 (必须修复)
{'='*60}

"""
    if analysis['issues']:
        for issue in analysis['issues']:
            report += f"  • {issue}\n"
    else:
        report += "  ✓ 无严重问题\n"
    
    report += f"""
{'='*60}
⚠️ 警告 (建议修复)
{'='*60}

"""
    if analysis['warnings']:
        for warning in analysis['warnings']:
            report += f"  • {warning}\n"
    else:
        report += "  ✓ 无警告\n"
    
    report += f"""
{'='*60}
💡 改进建议
{'='*60}

"""
    if analysis['suggestions']:
        for suggestion in analysis['suggestions']:
            report += f"  • {suggestion}\n"
    else:
        report += "  ✓ 无改进建议\n"
    
    report += f"""
{'='*60}
📋 合规性评分
{'='*60}

"""
    # 计算评分
    score = 100
    score -= len(analysis['issues']) * 15
    score -= len(analysis['warnings']) * 5
    score -= len(analysis['suggestions']) * 2
    score = max(0, min(100, score))
    
    if score >= 90:
        grade = "A (优秀)"
        emoji = "🌟"
    elif score >= 80:
        grade = "B (良好)"
        emoji = "✅"
    elif score >= 70:
        grade = "C (一般)"
        emoji = "⚠️"
    elif score >= 60:
        grade = "D (较差)"
        emoji = "❌"
    else:
        grade = "F (不合格)"
        emoji = "🚫"
    
    report += f"  {emoji} 综合评分: {score}/100 ({grade})\n"
    
    report += f"""
{'='*60}
🔧 修复优先级
{'='*60}

  高优先级:
"""
    if analysis['issues']:
        for issue in analysis['issues'][:3]:
            report += f"    1. {issue}\n"
    else:
        report += "    无\n"
    
    report += """
  中优先级:
"""
    if analysis['warnings']:
        for warning in analysis['warnings'][:3]:
            report += f"    • {warning}\n"
    else:
        report += "    无\n"
    
    report += """
  低优先级:
"""
    if analysis['suggestions']:
        for suggestion in analysis['suggestions'][:3]:
            report += f"    • {suggestion}\n"
    else:
        report += "    无\n"
    
    report += f"""
{'='*60}
"""
    
    return report


if __name__ == '__main__':
    # 分析项目
    graph_path = 'output/medium-project.graph.json'
    graph = load_graph(graph_path)
    
    # 运行合规性分析
    analysis = analyze_compliance(graph)
    
    # 生成报告
    report = generate_report('medium-project', analysis)
    
    # 打印报告
    print(report)
    
    # 保存报告
    with open('compliance_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n报告已保存到: compliance_report.txt")