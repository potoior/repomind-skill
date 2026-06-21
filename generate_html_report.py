#!/usr/bin/env python3
"""生成HTML格式的合规性报告"""

import json
from datetime import datetime


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
        found_by_path = any(any(kw in path for kw in keywords) for path in doc_paths)
        found_by_name = any(any(kw in name for kw in keywords) for name in doc_names)
        
        if not found_by_path and not found_by_name:
            issues.append(f"缺少必要文档: {doc_key}")
    
    # 2. 检查模块描述
    modules = [e for e in entities if e['type'] == 'Module']
    modules_without_desc = [m for m in modules if not m.get('description')]
    if modules_without_desc:
        warnings.append(f"{len(modules_without_desc)} 个模块缺少描述")
    
    # 3. 检查孤立实体
    connected_entities = set()
    for r in relations:
        connected_entities.add(r['source'].lower())
        connected_entities.add(r['target'].lower())
    
    ignore_types = {'Command', 'Document'}
    orphaned = [e for e in entities if e['name'].lower() not in connected_entities and e['type'] not in ignore_types]
    if orphaned:
        warnings.append(f"{len(orphaned)} 个孤立实体 (无关联关系)")
    
    # 4. 检查文档覆盖
    doc_relations = [r for r in relations if r['type'] == 'documents']
    documented_modules = set(r['target'] for r in doc_relations)
    undocumented = [m for m in modules if m['name'] not in documented_modules]
    if undocumented:
        warnings.append(f"{len(undocumented)} 个模块缺少文档引用")
    
    # 5. 检查技术栈复杂度
    databases = [e for e in entities if e['type'] == 'Database']
    if len(databases) > 3:
        suggestions.append(f"使用了 {len(databases)} 种数据库，考虑减少技术栈复杂度")
    
    # 计算评分
    score = 100
    score -= len(issues) * 15
    score -= len(warnings) * 5
    score -= len(suggestions) * 2
    score = max(0, min(100, score))
    
    return {
        'issues': issues,
        'warnings': warnings,
        'suggestions': suggestions,
        'score': score,
        'stats': {
            'total_entities': len(entities),
            'total_relations': len(relations),
            'documents': len(documents),
            'modules': len(modules),
            'orphaned_entities': len(orphaned),
            'undocumented_modules': len(undocumented)
        }
    }


def generate_html_report(project_name: str, analysis: dict, graph: dict) -> str:
    """生成HTML报告"""
    score = analysis['score']
    
    if score >= 90:
        grade = "A (优秀)"
        grade_color = "#28a745"
        grade_bg = "#d4edda"
    elif score >= 80:
        grade = "B (良好)"
        grade_color = "#17a2b8"
        grade_bg = "#d1ecf1"
    elif score >= 70:
        grade = "C (一般)"
        grade_color = "#ffc107"
        grade_bg = "#fff3cd"
    elif score >= 60:
        grade = "D (较差)"
        grade_color = "#fd7e14"
        grade_bg = "#ffeaa7"
    else:
        grade = "F (不合格)"
        grade_color = "#dc3545"
        grade_bg = "#f8d7da"
    
    # 统计各类型实体
    entity_types = {}
    for e in graph['entities']:
        t = e['type']
        entity_types[t] = entity_types.get(t, 0) + 1
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} - 合规性分析报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 10px; margin-bottom: 30px; text-align: center; }}
        .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; font-size: 14px; }}
        .score-card {{ background: {grade_bg}; border: 2px solid {grade_color}; border-radius: 10px; padding: 30px; text-align: center; margin-bottom: 30px; }}
        .score-number {{ font-size: 72px; font-weight: bold; color: {grade_color}; }}
        .score-grade {{ font-size: 24px; color: {grade_color}; margin-top: 10px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
        .stat-number {{ font-size: 36px; font-weight: bold; color: #667eea; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        .section {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .section h2 {{ color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #667eea; }}
        .issue {{ padding: 15px; margin-bottom: 10px; border-radius: 5px; }}
        .issue-error {{ background: #f8d7da; border-left: 4px solid #dc3545; }}
        .issue-warning {{ background: #fff3cd; border-left: 4px solid #ffc107; }}
        .issue-info {{ background: #d1ecf1; border-left: 4px solid #17a2b8; }}
        .issue-title {{ font-weight: bold; margin-bottom: 5px; }}
        .issue-desc {{ color: #666; font-size: 14px; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
        .badge-error {{ background: #dc3545; color: white; }}
        .badge-warning {{ background: #ffc107; color: #333; }}
        .badge-info {{ background: #17a2b8; color: white; }}
        .progress-bar {{ height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; margin-top: 20px; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, {grade_color}, {grade_color}88); border-radius: 10px; transition: width 0.3s; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        tr:hover {{ background: #f5f5f5; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {project_name} 合规性分析报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="score-card">
            <div class="score-number">{score}</div>
            <div class="score-grade">{grade}</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {score}%"></div>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{analysis['stats']['total_entities']}</div>
                <div class="stat-label">实体总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{analysis['stats']['total_relations']}</div>
                <div class="stat-label">关系总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{analysis['stats']['documents']}</div>
                <div class="stat-label">文档数量</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{analysis['stats']['modules']}</div>
                <div class="stat-label">模块数量</div>
            </div>
        </div>
        
        <div class="section">
            <h2>❌ 严重问题 ({len(analysis['issues'])})</h2>
"""
    
    if analysis['issues']:
        for issue in analysis['issues']:
            html += f"""            <div class="issue issue-error">
                <div class="issue-title"><span class="badge badge-error">严重</span> {issue}</div>
                <div class="issue-desc">必须修复此问题以确保项目质量</div>
            </div>
"""
    else:
        html += """            <div class="issue issue-info">
                <div class="issue-title">✓ 无严重问题</div>
                <div class="issue-desc">项目文档完整性良好</div>
            </div>
"""
    
    html += f"""        </div>
        
        <div class="section">
            <h2>⚠️ 警告 ({len(analysis['warnings'])})</h2>
"""
    
    if analysis['warnings']:
        for warning in analysis['warnings']:
            html += f"""            <div class="issue issue-warning">
                <div class="issue-title"><span class="badge badge-warning">警告</span> {warning}</div>
                <div class="issue-desc">建议修复以提高代码质量</div>
            </div>
"""
    else:
        html += """            <div class="issue issue-info">
                <div class="issue-title">✓ 无警告</div>
                <div class="issue-desc">项目结构良好</div>
            </div>
"""
    
    html += f"""        </div>
        
        <div class="section">
            <h2>💡 改进建议 ({len(analysis['suggestions'])})</h2>
"""
    
    if analysis['suggestions']:
        for suggestion in analysis['suggestions']:
            html += f"""            <div class="issue issue-info">
                <div class="issue-title"><span class="badge badge-info">建议</span> {suggestion}</div>
                <div class="issue-desc">可选改进项，提升项目质量</div>
            </div>
"""
    else:
        html += """            <div class="issue issue-info">
                <div class="issue-title">✓ 无改进建议</div>
                <div class="issue-desc">项目结构优秀</div>
            </div>
"""
    
    html += """        </div>
        
        <div class="section">
            <h2>📊 实体类型分布</h2>
            <table>
                <tr><th>类型</th><th>数量</th><th>占比</th></tr>
"""
    
    total = analysis['stats']['total_entities']
    for type_name, count in sorted(entity_types.items(), key=lambda x: -x[1]):
        percentage = f"{count/total*100:.1f}%"
        html += f"""                <tr>
                    <td>{type_name}</td>
                    <td>{count}</td>
                    <td>{percentage}</td>
                </tr>
"""
    
    html += """            </table>
        </div>
        
        <div class="footer">
            <p>由 RepoMind 生成 | 版本 2.0</p>
        </div>
    </div>
</body>
</html>"""
    
    return html


if __name__ == '__main__':
    # 分析项目
    graph_path = 'output/medium-project.graph.json'
    graph = load_graph(graph_path)
    
    # 运行合规性分析
    analysis = analyze_compliance(graph)
    
    # 生成HTML报告
    html = generate_html_report('medium-project', analysis, graph)
    
    # 保存报告
    with open('compliance_report.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("HTML报告已生成: compliance_report.html")