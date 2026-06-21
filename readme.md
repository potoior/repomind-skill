# RepoMind Skill - GitHub Knowledge Graph CLI

一个智能的项目知识图谱生成工具，能够自动分析代码仓库，提取实体关系，生成可视化图谱。

## 功能特性

- **自动扫描** - 递归扫描目录，识别Markdown和代码文件
- **智能提取** - 从文档和代码中提取实体、关系、技术栈
- **知识图谱** - 生成JSON格式的知识图谱
- **可视化** - 生成交互式HTML图谱可视化
- **智能问答** - 支持自然语言查询项目信息
- **多格式导出** - 支持JSON、CSV、Markdown格式导出

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

### 分析项目

```bash
python cli.py analyze /path/to/project
```

### 查看摘要

```bash
python cli.py summary
```

### 查询知识图谱

```bash
python cli.py query "有哪些模块"
python cli.py query "技术栈是什么"
python cli.py query "数据库有哪些"
```

### 交互式查询

```bash
python cli.py interactive
```

### 导出图谱

```bash
python cli.py export -f json
python cli.py export -f csv
python cli.py export -f markdown
```

### 列出已分析项目

```bash
python cli.py list
```

## 支持的查询

- `模块` - 查看所有模块
- `技术栈` - 查看技术栈
- `数据库` - 查看数据库
- `工具` - 查看工具
- `<实体名>是什么` - 查看实体详情
- `<实体名>依赖什么` - 查看依赖关系

## 输出示例

```
┌─────────────────────── 项目分析报告 ───────────────────────┐
│ 类型      │ 数量                                            │
├───────────┼─────────────────────────────────────────────────┤
│ Module    │   29                                            │
│ Feature   │   10                                            │
│ Command   │    7                                            │
│ Document  │    5                                            │
│ Database  │    4                                            │
│ Framework │    3                                            │
└───────────┴─────────────────────────────────────────────────┘
```

## 技术栈

- Python 3.11+
- Click - CLI框架
- Rich - 终端美化
- Pydantic - 数据模型
- GitPython - Git操作

## 项目结构

```
repomind-skill/
├── cli.py                  # CLI入口
├── main.py                 # 交互式入口
├── requirements.txt        # 依赖
├── src/
│   ├── models.py          # 数据模型
│   ├── repository_loader.py # 仓库加载
│   ├── knowledge_extractor.py # 知识提取
│   ├── graph_builder.py   # 图谱构建
│   ├── query_engine.py    # 查询引擎
│   └── qa_engine.py       # 问答引擎
├── tests/                 # 测试
└── data/                  # 示例数据
```

## License

MIT