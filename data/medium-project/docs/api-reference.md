# API参考

## Pipeline

数据管道核心类。

### 方法

#### `source(source)`
设置数据源。

```python
pipeline.source(CSVSource("data.csv"))
```

#### `transform(transform)`
添加转换器。

```python
pipeline.transform(FilterTransform())
```

#### `sink(sink)`
设置数据输出。

```python
pipeline.sink(PostgresSink("table"))
```

#### `run()`
运行管道。

```python
pipeline.run()
```

#### `stop()`
停止管道。

```python
pipeline.stop()
```

## Source

数据源基类。

### 内置数据源

- `CSVSource` - CSV文件
- `JSONSource` - JSON文件
- `PostgresSource` - PostgreSQL
- `MySQLSource` - MySQL
- `KafkaSource` - Kafka
- `S3Source` - AWS S3
- `APISource` - REST API

### 自定义数据源

```python
from dataflow.source import Source

class MySource(Source):
    def read(self):
        # 实现读取逻辑
        yield {"key": "value"}
```

## Transform

转换器基类。

### 内置转换器

- `Map` - 映射转换
- `Filter` - 过滤
- `FlatMap` - 扁平化
- `Aggregate` - 聚合
- `Join` - 连接
- `Window` - 窗口
- `Dedup` - 去重

### 自定义转换器

```python
from dataflow.transform import Transform

class MyTransform(Transform):
    def process(self, record):
        # 实现转换逻辑
        return transformed_record
```

## Sink

数据输出基类。

### 内置输出器

- `PostgresSink` - PostgreSQL
- `MySQLSink` - MySQL
- `CSVSink` - CSV文件
- `JSONSink` - JSON文件
- `KafkaSink` - Kafka
- `S3Sink` - AWS S3

### 自定义输出器

```python
from dataflow.sink import Sink

class MySink(Sink):
    def write(self, records):
        # 实现写入逻辑
        pass
```

## Monitor

监控和告警。

### 方法

#### `get_metrics()`
获取管道指标。

```python
metrics = pipeline.get_metrics()
print(metrics.throughput)
print(metrics.latency)
print(metrics.errors)
```

#### `set_alert(condition, callback)`
设置告警。

```python
pipeline.set_alert(
    condition=lambda m: m.errors > 100,
    callback=lambda: send_notification()
)
```