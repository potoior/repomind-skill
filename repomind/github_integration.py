"""GitHub集成 - 克隆仓库并分析"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class GitHubRepo:
    """GitHub仓库信息"""
    owner: str
    name: str
    url: str
    branch: str = "main"
    local_path: Optional[str] = None


def parse_github_url(url: str) -> GitHubRepo:
    """
    解析GitHub URL
    
    支持格式:
    - https://github.com/owner/repo
    - git@github.com:owner/repo.git
    - owner/repo
    """
    url = url.strip().rstrip('/')
    
    # SSH格式
    if url.startswith('git@github.com:'):
        path = url.replace('git@github.com:', '').replace('.git', '')
        parts = path.split('/')
        if len(parts) == 2:
            return GitHubRepo(
                owner=parts[0],
                name=parts[1],
                url=f"https://github.com/{parts[0]}/{parts[1]}"
            )
    
    # HTTPS格式
    if 'github.com' in url:
        parts = url.split('github.com/')[-1].split('/')
        if len(parts) >= 2:
            return GitHubRepo(
                owner=parts[0],
                name=parts[1].replace('.git', ''),
                url=f"https://github.com/{parts[0]}/{parts[1].replace('.git', '')}"
            )
    
    # 短格式: owner/repo
    parts = url.split('/')
    if len(parts) == 2:
        return GitHubRepo(
            owner=parts[0],
            name=parts[1],
            url=f"https://github.com/{parts[0]}/{parts[1]}"
        )
    
    raise ValueError(f"无法解析GitHub URL: {url}")


def clone_repo(repo: GitHubRepo, output_dir: str = "repos", branch: str = None) -> str:
    """
    克隆GitHub仓库
    
    Args:
        repo: GitHub仓库信息
        output_dir: 输出目录
        branch: 分支名称
        
    Returns:
        克隆后的本地路径
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    local_path = output_path / repo.name
    
    if local_path.exists():
        # 如果已存在，执行git pull
        try:
            subprocess.run(
                ["git", "pull"],
                cwd=str(local_path),
                capture_output=True,
                text=True,
                check=True
            )
            return str(local_path)
        except subprocess.CalledProcessError:
            pass
    
    # 克隆仓库
    cmd = ["git", "clone"]
    if branch:
        cmd.extend(["-b", branch])
    cmd.extend([repo.url, str(local_path)])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"克隆失败: {result.stderr}")
    
    repo.local_path = str(local_path)
    return str(local_path)


def get_repo_info(local_path: str) -> Dict[str, Any]:
    """
    获取仓库信息
    
    Args:
        local_path: 本地仓库路径
        
    Returns:
        仓库信息字典
    """
    info = {}
    
    try:
        # 获取当前分支
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=local_path,
            capture_output=True,
            text=True
        )
        info['branch'] = result.stdout.strip()
        
        # 获取最新提交
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H|%s|%an|%ad", "--date=short"],
            cwd=local_path,
            capture_output=True,
            text=True
        )
        if result.stdout:
            parts = result.stdout.strip().split('|')
            if len(parts) == 4:
                info['last_commit'] = {
                    'hash': parts[0],
                    'message': parts[1],
                    'author': parts[2],
                    'date': parts[3]
                }
        
        # 获取远程URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=local_path,
            capture_output=True,
            text=True
        )
        info['remote_url'] = result.stdout.strip()
        
        # 获取文件统计
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=local_path,
            capture_output=True,
            text=True
        )
        files = result.stdout.strip().split('\n')
        info['total_files'] = len(files)
        
        # 按扩展名统计
        ext_counts = {}
        for f in files:
            ext = Path(f).suffix or '无扩展名'
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
        info['file_types'] = dict(sorted(ext_counts.items(), key=lambda x: -x[1])[:10])
        
    except Exception as e:
        info['error'] = str(e)
    
    return info


def list_branches(local_path: str) -> list:
    """列出所有分支"""
    result = subprocess.run(
        ["git", "branch", "-a"],
        cwd=local_path,
        capture_output=True,
        text=True
    )
    
    branches = []
    for line in result.stdout.split('\n'):
        line = line.strip()
        if line:
            current = line.startswith('*')
            name = line.replace('* ', '').strip()
            if name:
                branches.append({
                    'name': name,
                    'current': current
                })
    
    return branches
