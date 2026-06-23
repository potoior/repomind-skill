"""Git历史分析 - 分析代码演变和贡献者图谱"""

import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict
import json


@dataclass
class GitCommit:
    """Git提交信息"""
    hash: str
    message: str
    author: str
    email: str
    date: str
    files_changed: int
    insertions: int
    deletions: int


@dataclass
class Contributor:
    """贡献者信息"""
    name: str
    email: str
    commits: int
    insertions: int
    deletions: int
    files_touched: set


@dataclass
class FileHistory:
    """文件历史"""
    path: str
    commits: int
    authors: List[str]
    last_modified: str
    total_changes: int


def get_commit_history(repo_path: str, max_commits: int = 100, since: str = None) -> List[GitCommit]:
    """
    获取提交历史
    
    Args:
        repo_path: 仓库路径
        max_commits: 最大提交数
        since: 起始日期 (YYYY-MM-DD)
        
    Returns:
        提交列表
    """
    cmd = [
        "git", "log",
        f"--max-count={max_commits}",
        "--format=%H|%s|%ae|%ad",
        "--date=short",
        "--numstat"
    ]
    
    if since:
        cmd.append(f"--since={since}")
    
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    
    if result.returncode != 0:
        return []
    
    commits = []
    current_commit = None
    
    for line in result.stdout.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        if '|' in line and len(line.split('|')) == 4:
            if current_commit:
                commits.append(current_commit)
            
            parts = line.split('|')
            current_commit = GitCommit(
                hash=parts[0],
                message=parts[1],
                author=parts[2].split('@')[0],
                email=parts[2],
                date=parts[3],
                files_changed=0,
                insertions=0,
                deletions=0
            )
        elif current_commit and line[0].isdigit():
            parts = line.split('\t')
            if len(parts) == 3:
                try:
                    ins = int(parts[0]) if parts[0] != '-' else 0
                    dels = int(parts[1]) if parts[1] != '-' else 0
                    current_commit.insertions += ins
                    current_commit.deletions += dels
                    current_commit.files_changed += 1
                except ValueError:
                    pass
    
    if current_commit:
        commits.append(current_commit)
    
    return commits


def get_contributors(repo_path: str, max_commits: int = 1000) -> List[Contributor]:
    """
    获取贡献者信息
    
    Args:
        repo_path: 仓库路径
        max_commits: 最大提交数
        
    Returns:
        贡献者列表
    """
    commits = get_commit_history(repo_path, max_commits)
    
    contributors = {}
    
    for commit in commits:
        if commit.email not in contributors:
            contributors[commit.email] = Contributor(
                name=commit.author,
                email=commit.email,
                commits=0,
                insertions=0,
                deletions=0,
                files_touched=set()
            )
        
        contributor = contributors[commit.email]
        contributor.commits += 1
        contributor.insertions += commit.insertions
        contributor.deletions += commit.deletions
    
    return sorted(contributors.values(), key=lambda c: c.commits, reverse=True)


def get_file_history(repo_path: str, file_path: str) -> Dict:
    """
    获取文件历史
    
    Args:
        repo_path: 仓库路径
        file_path: 文件路径
        
    Returns:
        文件历史信息
    """
    cmd = [
        "git", "log",
        "--format=%H|%s|%ae|%ad",
        "--date=short",
        "--follow",
        file_path
    ]
    
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    
    if result.returncode != 0:
        return None
    
    commits = []
    authors = set()
    
    for line in result.stdout.split('\n'):
        line = line.strip()
        if not line or '|' not in line:
            continue
        
        parts = line.split('|')
        if len(parts) == 4:
            commits.append({
                'hash': parts[0],
                'message': parts[1],
                'author': parts[2],
                'date': parts[3]
            })
            authors.add(parts[2])
    
    return {
        'file': file_path,
        'total_commits': len(commits),
        'authors': list(authors),
        'commits': commits[:50]  # 最近50个提交
    }


def get_code_churn(repo_path: str, since: str = None) -> Dict:
    """
    计算代码流失率
    
    Args:
        repo_path: 仓库路径
        since: 起始日期
        
    Returns:
        代码流失统计
    """
    cmd = [
        "git", "log",
        "--format=%ad",
        "--date=short",
        "--numstat"
    ]
    
    if since:
        cmd.append(f"--since={since}")
    
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    
    if result.returncode != 0:
        return {}
    
    daily_stats = defaultdict(lambda: {'insertions': 0, 'deletions': 0, 'files': 0})
    current_date = None
    
    for line in result.stdout.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        if len(line) == 10 and line[4] == '-' and line[7] == '-':
            current_date = line
        elif current_date and line[0].isdigit():
            parts = line.split('\t')
            if len(parts) == 3:
                try:
                    ins = int(parts[0]) if parts[0] != '-' else 0
                    dels = int(parts[1]) if parts[1] != '-' else 0
                    daily_stats[current_date]['insertions'] += ins
                    daily_stats[current_date]['deletions'] += dels
                    daily_stats[current_date]['files'] += 1
                except ValueError:
                    pass
    
    return dict(daily_stats)


def generate_contributor_graph(contributors: List[Contributor], output_file: str = None) -> str:
    """
    生成贡献者图谱（Mermaid格式）
    
    Args:
        contributors: 贡献者列表
        output_file: 输出文件
        
    Returns:
        Mermaid图代码
    """
    lines = ["graph TD"]
    lines.append("    classDef topContributor fill:#4CAF50,stroke:#388E3C,color:white")
    lines.append("    classDef contributor fill:#2196F3,stroke:#1565C0,color:white")
    lines.append("")
    
    # 取前10个贡献者
    top_contributors = contributors[:10]
    
    for i, contributor in enumerate(top_contributors):
        node_id = f"C{i}"
        name = contributor.name.replace(' ', '_')
        label = f"{name}\\n{contributor.commits}次提交"
        
        css_class = "topContributor" if i == 0 else "contributor"
        lines.append(f'    {node_id}["{label}"]:::{css_class}')
    
    lines.append("")
    
    # 添加提交量连接
    if len(top_contributors) > 1:
        for i in range(1, len(top_contributors)):
            lines.append(f"    C0 -.->|协作| C{i}")
    
    mermaid = "\n".join(lines)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 贡献者图谱\n\n")
            f.write("```mermaid\n")
            f.write(mermaid)
            f.write("\n```\n")
    
    return mermaid


def analyze_repo_evolution(repo_path: str, max_commits: int = 100) -> Dict:
    """
    分析仓库演变
    
    Args:
        repo_path: 仓库路径
        max_commits: 最大提交数
        
    Returns:
        演变分析结果
    """
    commits = get_commit_history(repo_path, max_commits)
    
    if not commits:
        return {}
    
    # 统计每月提交量
    monthly_commits = defaultdict(int)
    for commit in commits:
        month = commit.date[:7]  # YYYY-MM
        monthly_commits[month] += 1
    
    # 统计文件类型变化
    file_type_changes = defaultdict(int)
    
    # 计算总代码变化
    total_insertions = sum(c.insertions for c in commits)
    total_deletions = sum(c.deletions for c in commits)
    
    return {
        'total_commits': len(commits),
        'total_insertions': total_insertions,
        'total_deletions': total_deletions,
        'net_change': total_insertions - total_deletions,
        'monthly_commits': dict(sorted(monthly_commits.items())),
        'first_commit': commits[-1].date if commits else None,
        'last_commit': commits[0].date if commits else None,
    }
