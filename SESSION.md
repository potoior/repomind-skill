# 开发会话记录 - GitHub Knowledge Graph CLI

## 会话概述

本次会话从零开始构建了一个完整的GitHub知识图谱CLI工具，支持自动扫描代码仓库、提取实体关系、生成可视化图谱。

## 开发时间线

### 1. 初始阶段 - 阅读需求

- 阅读 `readme.md` 了解项目需求
- 确定MVP目标：导入仓库、解析Markdown、提取实体关系、生成知识图谱JSON

### 2. MVP构建

创建了基础项目结构：
```
src/
├── models.py              # 数据模型（Entity, Relation, Document）
├── repository_loader.py   # 仓库加载器
├── document_parser.py     # 文档解析器
├── knowledge_extractor.py # 知识提取器
├── graph_builder.py       # 图谱构建器
├── query_engine.py        # 查询引擎
└── qa_engine.py           # 问答引擎
```

### 3. 测试运行

- 修复了 `EntityType.TOOL` 缺失问题
- 修复了文件编码问题（支持UTF-8、UTF-16等）
- 创建了本地测试仓库验证功能

### 4. 分析中型项目

- 创建了模拟中型项目 `data/medium-project/`
- 包含5个Markdown文档和4个Python代码文件
- 测试了完整分析流程

### 5. 优化知识提取

**优化前 vs 优化后：**

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 实体数量 | 42 | 64 |
| 关系数量 | 31 | 108 |
| 实体类型 | 3种 | 8种 |
| 关系类型 | 1种 | 5种 |

**主要优化：**

1. **技术栈分类** - 正确识别Framework、Database、Tool、Protocol
2. **代码分析** - 从Python代码中提取类、函数、继承关系
3. **命令提取** - 从文档中提取CLI命令
4. **实体描述** - 从docstring和文档中提取描述
5. **关系推断** - 自动推断Framework使用Database的关系

### 6. 创建CLI工具

使用Click和Rich创建了完整的CLI工具：

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

# 导出图谱
python cli.py export -f json/csv/markdown
```

### 7. 上传到Git

- 初始化Git仓库
- 创建 `.gitignore` 排除缓存文件
- 提交并推送到 `git@github.com:potoior/repomind-skill.git`

## 关键技术决策

1. **数据模型** - 使用Pydantic定义Entity、Relation、Document等模型
2. **知识提取** - 基于规则的提取（非LLM依赖），支持离线使用
3. **存储格式** - 使用JSON存储知识图谱，无需数据库
4. **可视化** - 使用vis.js生成交互式HTML图谱
5. **CLI框架** - 使用Click + Rich提供美观的命令行体验

## 实体类型

- Project - 项目
- Module - 模块/类
- Feature - 功能/函数
- Document - 文档
- Framework - 框架
- Database - 数据库
- Tool - 工具
- Protocol - 协议
- Command - 命令
- API - API端点

## 关系类型

- uses - 使用
- contains - 包含
- documents - 文档化
- depends_on - 依赖
- extends - 继承
- implements - 实现

## 后续改进方向

1. 支持更多编程语言（JavaScript、TypeScript、Java等）
2. 集成LLM进行更智能的知识提取
3. 支持增量更新（只分析变更的文件）
4. 添加Neo4j等图数据库支持
5. 支持跨仓库分析

## 快速继续开发

```bash
# 克隆仓库
git clone git@github.com:potoior/repomind-skill.git
cd repomind-skill

# 安装依赖
pip install -r requirements.txt

# 测试分析
python cli.py analyze data/medium-project
python cli.py summary
python cli.py interactive
```

## 文件清单

```
repomind-skill/
├── cli.py                          # CLI入口（Click）
├── main.py                         # 交互式入口
├── requirements.txt                # 依赖
├── .gitignore                      # Git忽略规则
├── readme.md                       # 项目说明
├── SESSION.md                      # 本会话记录
├── src/
│   ├── __init__.py
│   ├── models.py                   # 数据模型
│   ├── repository_loader.py        # 仓库加载
│   ├── knowledge_extractor.py      # 知识提取（核心）
│   ├── graph_builder.py            # 图谱构建
│   ├── query_engine.py             # 查询引擎
│   └── qa_engine.py                # 问答引擎
├── tests/
│   └── test_basic.py               # 基础测试
└── data/
    └── medium-project/             # 示例项目
        ├── README.md
        ├── docs/
        └── src/
```