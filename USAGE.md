# GitHub Knowledge Graph Skill - MVP 使用指南

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
# 分析项目
python cli.py analyze /path/to/project

# 查看摘要
python cli.py summary

# 查询知识图谱
python cli.py query "模块"
python cli.py query "技术栈"

# 交互式查询
python cli.py interactive

# 指定项目名（当有多个分析结果时）
python cli.py -p medium-project summary
```

## 示例输出

分析完成后，程序会生成：
1. 知识图谱JSON文件 (`data/<repo_name>.graph.json`)
2. 可视化HTML文件 (`data/<repo_name>.graph.html`)

## 功能说明

- **Repository Loader**: 克隆GitHub仓库并加载Markdown文档
- **Knowledge Extractor**: 从文档中提取实体和关系
- **Graph Builder**: 构建知识图谱并生成可视化
- **Query Engine**: 查询知识图谱
- **QA Engine**: 回答关于项目的问题