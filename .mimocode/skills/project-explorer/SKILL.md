---
name: project-explorer
description: "Use when the user asks to read, understand, or explore an unfamiliar codebase or project — systematic exploration before planning or coding"
---

# Project Explorer

快速、系统地理解一个不熟悉的代码库。在做任何规划或编码之前先用这个 skill。

**触发时机：** 用户说"阅读一下这个项目"、"帮我看看这个代码库"、"这个项目是做什么的"等。

**Announce at start:** "我使用 project-explorer skill 来探索这个项目。"

---

## Phase 1 — 扫描结构

用 Glob 扫描项目文件树（排除 `node_modules`、`.git`、`__pycache__`、`dist`、`build` 等目录）。

识别：
- 项目根目录的关键文件（README、package.json、requirements.txt、Makefile、docker-compose 等）
- 源代码目录结构
- 配置文件（.env.example、config/、settings 等）
- 测试目录

**输出：** 文件树概览（不超过 30 行），标注关键目录的用途。

---

## Phase 2 — 读取核心文件

按优先级读取：

1. **README.md** — 项目目标、使用方式、架构说明
2. **依赖文件** — `package.json`、`requirements.txt`、`go.mod`、`Cargo.toml` 等
3. **入口文件** — `main.py`、`app.py`、`index.ts`、`main.go` 等
4. **配置文件** — `.env.example`、`config.py`、`settings.ts` 等
5. **路由/API 定义** — `routes.py`、`api/` 目录

对每个文件，只读前 50-100 行获取结构信息，除非需要深入理解特定逻辑。

---

## Phase 3 — 检查环境

用 Bash 检查：
- 运行时版本（Python/Node/Go 等）
- 依赖是否已安装（`node_modules` 是否存在、`pip list` 等）
- 环境变量配置（`.env` 是否存在）
- 数据库/外部服务依赖

---

## Phase 4 — 总结架构

输出一份结构化的项目概览：

```
## 项目概览

**一句话概括：** [项目做什么]

### 技术栈
| 层 | 技术 |
|---|---|
| 后端 | ... |
| 前端 | ... |
| 数据库 | ... |
| 部署 | ... |

### 核心模块
| 文件/目录 | 功能 |
|---|---|
| ... | ... |

### 运行方式
[启动命令和端口]

### 当前状态
[依赖是否就绪、能否直接运行、已知问题]
```

---

## 停止条件

- 完成 Phase 4 的项目概览输出后停止
- 不要自动开始修改代码或安装依赖
- 如果用户后续要求运行项目或做修改，那是另一个任务
