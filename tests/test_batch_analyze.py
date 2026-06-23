import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent))

from cli import cli


def test_batch_analyze_help():
    """测试 batch-analyze 命令帮助"""
    runner = CliRunner()
    result = runner.invoke(cli, ['batch-analyze', '--help'])
    assert result.exit_code == 0
    assert '批量分析多个目录' in result.output


def test_batch_analyze_with_parent_flag():
    """测试 --parent 选项在帮助中显示"""
    runner = CliRunner()
    result = runner.invoke(cli, ['batch-analyze', '--help'])
    assert '--parent' in result.output


def test_batch_analyze_with_llm_flag():
    """测试 --llm 选项在帮助中显示"""
    runner = CliRunner()
    result = runner.invoke(cli, ['batch-analyze', '--help'])
    assert '--llm' in result.output


def test_batch_analyze_no_args():
    """测试无参数时的错误提示"""
    runner = CliRunner()
    result = runner.invoke(cli, ['batch-analyze'])
    assert result.exit_code != 0


def test_batch_analyze_nonexistent_path():
    """测试不存在的路径"""
    runner = CliRunner()
    result = runner.invoke(cli, ['batch-analyze', '/nonexistent/path'])
    assert '不存在' in result.output or result.exit_code != 0


if __name__ == "__main__":
    test_batch_analyze_help()
    test_batch_analyze_with_parent_flag()
    test_batch_analyze_with_llm_flag()
    test_batch_analyze_no_args()
    test_batch_analyze_nonexistent_path()
    print("所有 batch_analyze 测试通过!")
