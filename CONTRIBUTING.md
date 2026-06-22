# 开发者指南

## 快速开始

### 1. 克隆项目

```bash
git clone git@github.com:potoior/repomind-skill.git
cd repomind-skill
```

### 2. 环境配置

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 3. 验证安装

```bash
# 运行测试
python tests/test_basic.py

# 分析示例项目
python cli.py analyze data/medium-project
python cli.py summary
```

---

## 项目架构

```
repomind-skill/
├── cli.py                      # CLI入口（Click框架）
├── src/
│   ├── models.py               # 数据模型定义
│   ├── repository_loader.py    # 仓库加载器
│   ├── knowledge_extractor.py  # 知识提取器（核心）
│   ├── graph_builder.py        # 图谱构建器
│   ├── query_engine.py         # 查询引擎
│   ├── qa_engine.py            # 问答引擎
│   └── flow_analyzer.py        # API流程分析器
├── tests/                      # 测试文件
└── data/                       # 示例数据
```

---

## 核心模块说明

### 1. models.py - 数据模型

定义了所有数据结构：
- `Entity` - 实体（Module, Feature, Document等）
- `Relation` - 关系（uses, contains, extends等）
- `Document` - 文档
- `KnowledgeGraph` - 知识图谱

### 2. knowledge_extractor.py - 知识提取器

**核心逻辑所在**，负责：
- 从Markdown提取模块、API、命令
- 从代码提取类、函数、继承关系
- 技术栈识别和分类
- 关系推断

### 3. repository_loader.py - 仓库加载器

负责：
- 本地目录扫描
- 文件编码处理
- Markdown和代码文件识别

---

## 常见开发任务

### 添加新的实体类型

1. 在 `src/models.py` 的 `EntityType` 中添加：
```python
class EntityType(str, Enum):
    # ... 现有类型
    NEW_TYPE = "NewType"
```

2. 在 `src/knowledge_extractor.py` 中添加提取逻辑

### 添加新的关系类型

1. 在 `src/models.py` 的 `RelationType` 中添加：
```python
class RelationType(str, Enum):
    # ... 现有类型
    NEW_RELATION = "new_relation"
```

2. 在提取器中添加关系推断逻辑

### 支持新的编程语言

1. 在 `src/repository_loader.py` 的 `_find_code_files` 中添加扩展名：
```python
extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.新扩展名'}
```

2. 在 `src/knowledge_extractor.py` 的 `_extract_from_code` 中添加解析逻辑

### 添加新的查询类型

在 `src/qa_engine.py` 的 `answer_question` 方法中添加：
```python
if any(word in question for word in ["新关键词"]):
    return self._answer_new_type(question)
```

---

## 运行测试

```bash
# 运行基础测试
python tests/test_basic.py

# 测试CLI
python cli.py analyze data/medium-project
python cli.py query "模块"
python cli.py interactive
```

---

## 调试技巧

### 查看提取结果

```python
from src.knowledge_extractor import KnowledgeExtractor
from src.repository_loader import RepositoryLoader

loader = RepositoryLoader()
context = loader.clone_repo("data/medium-project")
documents = loader.load_documents(context)
code_files = loader.load_code_files(context)

extractor = KnowledgeExtractor()
entities, relations = extractor.extract_from_documents(documents, code_files)

for e in entities:
    print(f"{e.type.value}: {e.name}")
```

### 查看生成的图谱

```python
import json
with open('output/medium-project.graph.json', 'r', encoding='utf-8') as f:
    graph = json.load(f)
    print(json.dumps(graph, indent=2, ensure_ascii=False))
```

---

## 提交规范

```bash
# 功能
git commit -m "feat: 添加XXX功能"

# 修复
git commit -m "fix: 修复XXX问题"

# 文档
git commit -m "docs: 更新XXX文档"

# 重构
git commit -m "refactor: 重构XXX模块"
```

---

## 后续改进方向

1. **LLM集成** - 使用大模型进行更智能的知识提取
2. **增量更新** - 只分析变更的文件
3. **图数据库** - 支持Neo4j存储
4. **跨仓库分析** - 支持多仓库关联分析
5. **Web界面** - 添加Web UI
6. **更多语言** - 支持JavaScript、Java、Go等

---

## 获取帮助

- 阅读 `SESSION.md` 了解开发背景
- 阅读 `readme.md` 了解使用方法
- 查看 `src/` 目录下的源码注释
