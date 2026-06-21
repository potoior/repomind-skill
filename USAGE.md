# GitHub Knowledge Graph Skill - MVP 使用指南

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
python main.py
```

## 可用命令

### 分析仓库
```
analyze https://github.com/username/repo
```

### 查询知识图谱
```
query 什么是MCP
query ModuleA依赖什么
query 有哪些模块
```

### 显示图谱摘要
```
show
```

### 导出图谱
```
export filename.json
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