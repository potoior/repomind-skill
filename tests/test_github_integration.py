import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from repomind.github_integration import parse_github_url, GitHubRepo


def test_parse_https_url():
    """测试解析HTTPS URL"""
    repo = parse_github_url("https://github.com/owner/repo")
    assert repo.owner == "owner"
    assert repo.name == "repo"
    assert repo.url == "https://github.com/owner/repo"


def test_parse_https_url_with_git():
    """测试解析带.git后缀的HTTPS URL"""
    repo = parse_github_url("https://github.com/owner/repo.git")
    assert repo.owner == "owner"
    assert repo.name == "repo"


def test_parse_ssh_url():
    """测试解析SSH URL"""
    repo = parse_github_url("git@github.com:owner/repo.git")
    assert repo.owner == "owner"
    assert repo.name == "repo"
    assert repo.url == "https://github.com/owner/repo"


def test_parse_short_format():
    """测试解析短格式"""
    repo = parse_github_url("owner/repo")
    assert repo.owner == "owner"
    assert repo.name == "repo"


def test_parse_url_with_trailing_slash():
    """测试解析带尾部斜杠的URL"""
    repo = parse_github_url("https://github.com/owner/repo/")
    assert repo.owner == "owner"
    assert repo.name == "repo"


def test_github_repo_dataclass():
    """测试GitHubRepo数据类"""
    repo = GitHubRepo(owner="test", name="repo", url="https://github.com/test/repo")
    assert repo.owner == "test"
    assert repo.name == "repo"
    assert repo.branch == "main"


if __name__ == "__main__":
    test_parse_https_url()
    test_parse_https_url_with_git()
    test_parse_ssh_url()
    test_parse_short_format()
    test_parse_url_with_trailing_slash()
    test_github_repo_dataclass()
    print("所有 github_integration 测试通过!")
