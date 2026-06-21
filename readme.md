# GitHub Knowledge Graph Skill

## 项目定位

GitHub Knowledge Graph Skill 是一个面向 AI Agent 的知识图谱引擎。

它能够自动分析 GitHub 仓库中的 Markdown 文档、代码结构、配置文件和 Wiki 内容，构建项目知识网络，并提供智能问答、关系推理和架构分析能力。

与传统 RAG 的区别：

传统方案：

Repository
→ Chunk
→ Embedding
→ Vector DB
→ Search

本项目：

Repository
→ Knowledge Extraction
→ Knowledge Graph
→ Embedding
→ Agent Reasoning

最终让 Agent 真正理解项目，而不仅仅是搜索项目。

------

# MVP 目标

V1 只实现以下能力：

1. 导入 GitHub 仓库
2. 解析 Markdown
3. 提取实体
4. 提取关系
5. 生成知识图谱 JSON
6. 提供问答能力

不接入 Neo4j。

不接入 Graph Database。

全部采用本地 JSON 存储。

------

# 用户场景

场景1

用户输入：

analyze https://github.com/xxx/project

系统输出：

项目名称
核心模块
技术栈
依赖关系

------

场景2

用户输入：

what is MCP

系统回答：

MCP 是项目中的协议层。

相关模块：

- agent
- skill
- connector

引用来源：

docs/mcp.md

------

场景3

用户输入：

show architecture

系统生成：

项目架构图

------

# 技术架构

GitHub Repository

↓

Repository Loader

↓

Document Parser

↓

Knowledge Extractor

↓

Knowledge Graph Builder

↓

JSON Storage

↓

Query Engine

↓

Agent

------

# 模块设计

## Repository Loader

功能：

克隆仓库

支持：

README.md
docs/
wiki/
examples/
CHANGELOG.md

忽略：

node_modules
dist
build

输出：

RepositoryContext

------

## Document Parser

输入：

Markdown 文件

输出：

Document

结构：

{
"path": "docs/install.md",
"title": "Installation",
"content": "...",
"headings": []
}

------

## Knowledge Extractor

调用 LLM 提取：

Entity
Relation
Property

示例：

输入：

OpenClaw supports MCP.

输出：

{
"entities": [
{
"name": "OpenClaw",
"type": "Project"
},
{
"name": "MCP",
"type": "Protocol"
}
],
"relations": [
{
"source": "OpenClaw",
"target": "MCP",
"type": "supports"
}
]
}

------

# Entity 类型

Project

Module

Service

Protocol

Skill

Framework

Database

API

Configuration

Command

Feature

Document

------

# Relation 类型

depends_on

supports

uses

contains

implements

extends

connects_to

calls

references

documents

belongs_to

------

# Graph Builder

合并所有实体

去重

生成统一知识图谱

输出：

project.graph.json

结构：

{
"entities": [],
"relations": []
}

------

# Query Engine

支持：

find_entity(name)

find_relation(entity)

find_dependencies(module)

find_documents(entity)

find_related(entity)

------

# AI 问答

工作流程：

用户提问

↓

检索相关实体

↓

检索关系

↓

检索原始文档

↓

生成回答

避免幻觉。

所有回答必须附带来源文件。

------

# 可视化

生成 graph.html

使用：

vis.js

或者

Cytoscape.js

展示：

节点

关系

依赖链

------

# Skill 命令

analyze_repo

分析仓库

参数：

repo_url

------

query_graph

查询知识图谱

参数：

question

------

show_graph

打开图谱页面

------

export_graph

导出 JSON

------

# 输出示例

项目：

OpenClaw

实体数量：

324

关系数量：

918

核心模块：

- Agent Core
- Skill Manager
- MCP Layer
- API Gateway

主要依赖：

- Docker
- Python
- vLLM

发现文档：

- README.md
- docs/install.md
- docs/mcp.md

知识图谱已生成：

project.graph.json

可视化已生成：

graph.html

------

# V2 规划

Neo4j 支持

GraphRAG

跨仓库分析

Issue 分析

PR 分析

Commit 分析

自动生成架构文档

自动发现文档冲突

自动发现缺失文档

多仓库知识融合

------

# 技术栈建议

Python 3.12

LangChain

Pydantic

NetworkX

Cytoscape.js

SentenceTransformers

Qwen3

Hermes Skill SDK

MCP SDK

------

# 成功标准

分析一个中型 GitHub 项目：

1000+ Markdown 节点

构建知识图谱时间：

小于3分钟

问答响应：

小于5秒

知识图谱准确率：

80%以上

支持离线部署

支持本地模型

支持 OpenClaw/Hermes Skill 安装