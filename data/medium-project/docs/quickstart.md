# 快速入门

## 5分钟上手DataFlow

本指南将帮助您快速创建第一个数据管道。

## 第一步：初始化项目

```bash
dataflow init my-first-pipeline
cd my-first-pipeline
```

这会创建以下结构：

```
my-first-pipeline/
├── dataflow.yaml
├── pipeline.py
├── transforms/
├── sources/
├── sinks/
└── tests/
```

## 第二步：创建数据源

创建文件 `sources/csv_source.py`:

```python
from dataflow.source import CSVSource

class MyCSVSource(CSVSource):
    def __init__(self, file_path):
        super().__init__(file_path)
        self.file_path = file_path
    
    def read(self):
        return self.parse_csv(self.file_path)
```

## 第三步：创建转换器

创建文件 `transforms/filter_transform.py`:

```python
from dataflow.transform import Transform

class FilterActive(Transform):
    def process(self, record):
        if record.get("status") == "active":
            return record
        return None
```

## 第四步：创建数据输出

创建文件 `sinks/postgres_sink.py`:

```python
from dataflow.sink import PostgresSink

class MyPostgresSink(PostgresSink):
    def __init__(self, table_name):
        super().__init__(table_name)
        self.table_name = table_name
    
    def write(self, records):
        self.batch_insert(self.table_name, records)
```

## 第五步：组装管道

编辑 `pipeline.py`:

```python
from dataflow import Pipeline
from sources.csv_source import MyCSVSource
from transforms.filter_transform import FilterActive
from sinks.postgres_sink import MyPostgresSink

def create_pipeline():
    pipeline = Pipeline("my-etl")
    
    # 设置数据源
    pipeline.source(MyCSVSource("data/input.csv"))
    
    # 添加转换
    pipeline.transform(FilterActive())
    
    # 设置输出
    pipeline.sink(MyPostgresSink("active_users"))
    
    return pipeline

if __name__ == "__main__":
    pipeline = create_pipeline()
    pipeline.run()
```

## 第六步：运行管道

```bash
dataflow run pipeline.py
```

## 查看结果

```bash
dataflow status my-etl
dataflow logs my-etl
```

## 下一步

- 阅读 [API参考](api-reference.md) 了解更多API
- 查看 [示例项目](../examples/) 获取更多灵感
- 了解 [架构设计](architecture.md) 理解底层原理