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
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## ✨ 功能特性

- **🔍 自动扫描** - 递归扫描目录，识别Markdown和代码文件
- **🧠 智能提取** - 从文档和代码中提取实体、关系、技术栈
- **📊 知识图谱** - 生成JSON格式的知识图谱
- **🌐 可视化** - 生成交互式HTML图谱可视化
- **💬 智能问答** - 支持自然语言查询项目信息
- **📤 多格式导出** - 支持JSON、CSV、Markdown、HTML格式导出
- **🔍 搜索功能** - 快速搜索实体
- **📦 依赖分析** - 分析模块依赖关系

---

## 🚀 快速开始

### 安装

```bash
git clone git@github.com:potoior/repomind-skill.git
cd repomind-skill
pip install -r requirements.txt
```

### 分析项目

```bash
python cli.py analyze /path/to/your/project
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

| 命令 | 说明 | 示例 |
|------|------|------|
| `analyze` | 分析本地目录 | `python cli.py analyze ./my-project` |
| `summary` | 显示分析摘要 | `python cli.py summary` |
| `query` | 查询知识图谱 | `python cli.py query "模块"` |
| `search` | 搜索实体 | `python cli.py search Pipeline` |
| `entity` | 查看实体详情 | `python cli.py entity Pipeline` |
| `deps` | 查看依赖关系 | `python cli.py deps Pipeline` |
| `export` | 导出图谱 | `python cli.py export -f html` |
| `list` | 列出已分析项目 | `python cli.py list` |
| `load` | 加载指定项目 | `python cli.py load my-project` |
| `interactive` | 交互式查询 | `python cli.py interactive` |
| `version` | 显示版本信息 | `python cli.py version` |
| `logo` | 显示Logo | `python cli.py logo` |

---

## 🎯 支持的查询

### 分类查询

- `模块` - 查看所有模块
- `技术栈` - 查看技术栈
- `数据库` - 查看数据库
- `工具` - 查看工具
- `协议` - 查看协议

### 实体查询

- `<实体名>是什么` - 查看实体详情
- `<实体名>依赖什么` - 查看依赖关系

### 搜索

- `search <关键词>` - 搜索实体

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
- **GitPython** - Git操作

---

## 📁 项目结构

```
repomind-skill/
├── cli.py                      # CLI入口
├── requirements.txt            # 依赖
├── readme.md                   # 项目说明
├── SESSION.md                  # 开发会话记录
├── CONTRIBUTING.md             # 开发者指南
├── src/
│   ├── __init__.py
│   ├── models.py               # 数据模型
│   ├── repository_loader.py    # 仓库加载
│   ├── knowledge_extractor.py  # 知识提取
│   ├── graph_builder.py        # 图谱构建
│   ├── query_engine.py         # 查询引擎
│   ├── qa_engine.py            # 问答引擎
│   └── flow_analyzer.py        # API流程分析
├── tests/
│   └── test_basic.py           # 基础测试
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
