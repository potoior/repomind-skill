# RepoMind - 智能项目知识图谱生成工具

<div align="center">

```
  ____                _           __  __            _ _
 |  _ \ ___  _ __   (_)_ __   |  \/  | ___ _ __ (_) |_ ___  _ __
 | |_) / _ \| '_ \  | | '_ \  | |\/| |/ _ \ '_ \| | __/ _ \| '__|
 |  _ < (_) | |_) | | | | | | | |  | |  __/ | | | | || (_) | |
 |_| \_\___/| .__/  |_|_| |_| |_|  |_|\___|_| |_|_|\__\___/|_|
            |_|
```

**智能项目知识图谱生成工具 v2.0**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-111%20passed-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## ✨ 功能特性

### 🔍 核心功能
- **自动扫描** - 递归扫描目录，识别Markdown和代码文件
- **智能提取** - 从文档和代码中提取实体、关系、技术栈
- **LLM提取** - 支持OpenAI兼容API进行高质量知识提取
- **知识图谱** - 生成JSON格式的知识图谱
- **交互式可视化** - 生成支持搜索、筛选、详情查看的交互式HTML图谱

### 📊 分析功能
- **依赖分析** - 分析模块依赖关系
- **API流程分析** - 识别API端点和函数调用链
- **Mermaid流程图** - 生成API和调用链的Mermaid流程图
- **增量更新** - 只处理变化的文件，提高分析效率

### 🔎 查询功能
- **智能问答** - 支持自然语言查询项目信息
- **高级搜索** - 支持正则、模糊匹配、类型过滤
- **交互模式** - 支持Tab补全、历史记录的交互式查询

### 🛠️ 工具功能
- **批量分析** - 一次分析多个目录
- **Watch模式** - 监听文件变化，自动重新分析
- **图谱对比** - 比较两个项目图谱的差异
- **图谱合并** - 合并多个项目图谱
- **Daemon模式** - 常驻进程，消除重复启动开销
- **多格式导出** - 支持JSON、CSV、Markdown、HTML格式

---

## 🚀 快速开始

### 安装

```bash
git clone git@github.com:potoior/repomind-skill.git
cd repomind-skill
pip install -r requirements.txt
```

### 配置LLM API（可选）

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，填入API配置
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### 分析项目

```bash
# 基本分析
python cli.py analyze /path/to/your/project

# 使用LLM提取
python cli.py analyze /path/to/your/project --llm

# 增量更新
python cli.py analyze /path/to/your/project -i
```

### 查看摘要

```bash
python cli.py summary
```

### 查询知识图谱

```bash
python cli.py query "模块"
python cli.py query "技术栈"
python cli.py query "数据库"
```

### 交互式查询

```bash
python cli.py interactive
```

---

## 📖 命令大全

### 分析命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `analyze` | 分析本地目录 | `python cli.py analyze ./my-project` |
| `batch-analyze` | 批量分析多个目录 | `python cli.py batch-analyze dir1 dir2 dir3` |
| `watch` | 监听文件变化 | `python cli.py watch ./my-project` |
| `flow` | 分析API流程 | `python cli.py flow ./my-project` |

### 查询命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `summary` | 显示分析摘要 | `python cli.py summary` |
| `query` | 查询知识图谱 | `python cli.py query "模块"` |
| `search` | 搜索实体 | `python cli.py search Pipeline` |
| `search-advanced` | 高级搜索 | `python cli.py search-advanced "User" -t Module --regex` |
| `entity` | 查看实体详情 | `python cli.py entity Pipeline` |
| `deps` | 查看依赖关系 | `python cli.py deps Pipeline` |

### 图谱操作

| 命令 | 说明 | 示例 |
|------|------|------|
| `diff` | 比较图谱差异 | `python cli.py diff project-v1 project-v2` |
| `diff-html` | 生成对比报告 | `python cli.py diff-html project-v1 project-v2` |
| `merge` | 合并多个图谱 | `python cli.py merge p1 p2 p3 -o merged` |
| `export` | 导出图谱 | `python cli.py export -f html` |

### 流程图

| 命令 | 说明 | 示例 |
|------|------|------|
| `flow` | 分析API流程 | `python cli.py flow ./my-project` |
| `flow-detail` | 查看流程详情 | `python cli.py flow-detail -i 1` |
| `flowchart` | 生成流程图 | `python cli.py flowchart -i 1` |
| `flowcharts` | 生成所有流程图 | `python cli.py flowcharts` |

### 系统命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `list` | 列出已分析项目 | `python cli.py list` |
| `load` | 加载指定项目 | `python cli.py load my-project` |
| `serve` | 启动daemon服务器 | `python cli.py serve` |
| `stop` | 停止daemon服务器 | `python cli.py stop` |
| `interactive` | 交互式查询 | `python cli.py interactive` |
| `version` | 显示版本信息 | `python cli.py version` |
| `logo` | 显示Logo | `python cli.py logo` |

---

## 🎯 高级搜索

```bash
# 按类型过滤
python cli.py search-advanced "Service" -t Module -t Service

# 正则表达式
python cli.py search-advanced "^User.*" --regex

# 模糊匹配
python cli.py search-advanced "UsrService" --fuzzy --threshold 0.7

# 显示上下文
python cli.py search-advanced "Pipeline" --context
```

---

## 🔧 配置选项

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | API密钥 | - |
| `OPENAI_BASE_URL` | API地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 模型名称 | `gpt-4o-mini` |

### CLI全局选项

| 选项 | 说明 |
|------|------|
| `-o, --output` | 输出目录 |
| `-p, --project` | 指定项目名称 |

---

## 📊 输出示例

### 分析报告

```
           📊 medium-project 分析报告           
┌─────────────────┬──────┬──────────┬──────────┐
│ 类型            │ 图标 │     数量 │     占比 │
├─────────────────┼──────┼──────────┼──────────┤
│ Module          │ 📦   │       29 │    45.3% │
│ Feature         │ ⚡   │       10 │    15.6% │
│ Command         │ 💻   │        7 │    10.9% │
│ Document        │ 📄   │        5 │     7.8% │
│ Database        │ 🗄️    │        4 │     6.2% │
│ Framework       │ 🔧   │        3 │     4.7% │
└─────────────────┴──────┴──────────┴──────────┘
```

### 核心模块

```
📦 核心模块
├── Pipeline
├── Transform
├── Source
├── Sink
├── Scheduler
└── Monitor
```

---

## 🛠️ 技术栈

- **Python 3.11+** - 主要语言
- **Click** - CLI框架
- **Rich** - 终端美化
- **Pydantic** - 数据模型
- **vis.js** - 图谱可视化

---

## 📁 项目结构

```
repomind-skill/
├── cli.py                      # CLI入口
├── requirements.txt            # 依赖
├── readme.md                   # 项目说明
├── .env.example                # 环境变量模板
├── src/
│   ├── __init__.py
│   ├── models.py               # 数据模型
│   ├── repository_loader.py    # 仓库加载
│   ├── knowledge_extractor.py  # 知识提取
│   ├── graph_builder.py        # 图谱构建
│   ├── query_engine.py         # 查询引擎
│   ├── qa_engine.py            # 问答引擎
│   ├── flow_analyzer.py        # API流程分析
│   ├── renderers.py            # 渲染器
│   ├── incremental.py          # 增量更新
│   ├── llm_extractor.py        # LLM提取
│   ├── graph_diff.py           # 图谱对比
│   ├── graph_merge.py          # 图谱合并
│   ├── advanced_search.py      # 高级搜索
│   ├── file_watcher.py         # 文件监听
│   ├── server.py               # Daemon服务器
│   └── client.py               # Daemon客户端
├── tests/
│   ├── test_basic.py
│   ├── test_knowledge_extractor.py
│   ├── test_flow_analyzer.py
│   ├── test_incremental.py
│   ├── test_llm_extractor.py
│   ├── test_qa_engine.py
│   ├── test_interactive.py
│   ├── test_batch_analyze.py
│   ├── test_file_watcher.py
│   ├── test_graph_diff.py
│   ├── test_graph_merge.py
│   └── test_advanced_search.py
└── data/
    └── medium-project/         # 示例项目
```

---

## 🤝 贡献

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与开发。

---

## 📄 许可证

MIT License

---

## 🔗 链接

- [GitHub仓库](https://github.com/potoior/repomind-skill)
- [开发会话记录](SESSION.md)
- [开发者指南](CONTRIBUTING.md)
