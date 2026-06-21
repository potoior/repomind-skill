from abc import ABC, abstractmethod
from typing import Iterator, Any


class Sink(ABC):
    """数据输出基类。"""
    
    @abstractmethod
    def write(self, data: Iterator[Any]) -> None:
        """写入数据。"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """关闭输出。"""
        pass


class CSVSink(Sink):
    """CSV文件输出。"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def write(self, data: Iterator[dict]) -> None:
        import csv
        first = True
        with open(self.file_path, 'w', newline='') as f:
            for item in data:
                if first:
                    writer = csv.DictWriter(f, fieldnames=item.keys())
                    writer.writeheader()
                    first = False
                writer.writerow(item)
    
    def close(self) -> None:
        pass


class PostgresSink(Sink):
    """PostgreSQL输出。"""
    
    def __init__(self, connection_string: str, table: str):
        self.connection_string = connection_string
        self.table = table
    
    def write(self, data: Iterator[dict]) -> None:
        import psycopg2
        conn = psycopg2.connect(self.connection_string)
        cursor = conn.cursor()
        for item in data:
            columns = ', '.join(item.keys())
            placeholders = ', '.join(['%s'] * len(item))
            query = f"INSERT INTO {self.table} ({columns}) VALUES ({placeholders})"
            cursor.execute(query, list(item.values()))
        conn.commit()
        cursor.close()
        conn.close()
    
    def close(self) -> None:
        pass


class KafkaSink(Sink):
    """Kafka输出。"""
    
    def __init__(self, bootstrap_servers: str, topic: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
    
    def write(self, data: Iterator[dict]) -> None:
        from kafka import KafkaProducer
        import json
        producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        for item in data:
            producer.send(self.topic, value=item)
        producer.flush()
        producer.close()
    
    def close(self) -> None:
        pass