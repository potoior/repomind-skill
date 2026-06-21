# 安装指南

## 系统要求

- Python 3.11+
- Redis 7.0+
- PostgreSQL 15+
- Kafka 3.0+ (可选)

## 安装方式

### 方式一：pip安装

```bash
pip install dataflow
```

### 方式二：源码安装

```bash
git clone https://github.com/example/dataflow
cd dataflow
pip install -e .
```

### 方式三：Docker安装

```bash
docker pull dataflow/dataflow:latest
docker run -d dataflow/dataflow
```

## 依赖安装

### 核心依赖

```bash
pip install dataflow[core]
```

### 完整依赖

```bash
pip install dataflow[all]
```

### 可选依赖

- Kafka支持：`pip install dataflow[kafka]`
- Spark支持：`pip install dataflow[spark]`
- 监控支持：`pip install dataflow[monitor]`

## 配置

创建配置文件 `dataflow.yaml`:

```yaml
app:
  name: my-dataflow
  debug: false

database:
  host: localhost
  port: 5432
  name: dataflow
  user: postgres
  password: secret

redis:
  host: localhost
  port: 6379
  db: 0

kafka:
  brokers:
    - localhost:9092
  group-id: dataflow-group

logging:
  level: INFO
  format: json
```

## 验证安装

```bash
dataflow --version
dataflow doctor
```

## 故障排除

### 常见问题

1. **ImportError: No module named 'dataflow'**
   - 确认已正确安装：`pip show dataflow`

2. **连接Redis失败**
   - 检查Redis服务：`redis-cli ping`
   - 确认配置正确

3. **Kafka连接超时**
   - 检查Kafka服务：`kafka-topics.sh --list --bootstrap-server localhost:9092`

4. **数据库迁移失败**
   - 运行：`dataflow db upgrade`

## 升级

```bash
pip install --upgrade dataflow
dataflow db upgrade
```