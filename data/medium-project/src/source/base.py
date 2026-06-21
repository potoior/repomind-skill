from abc import ABC, abstractmethod
from typing import Iterator, Any


class Source(ABC):
    """数据源基类。"""
    
    @abstractmethod
    def read(self) -> Iterator[Any]:
        """读取数据。"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """关闭数据源。"""
        pass


class CSVSource(Source):
    """CSV文件数据源。"""
    
    def __init__(self, file_path: str, delimiter: str = ','):
        self.file_path = file_path
        self.delimiter = delimiter
    
    def read(self) -> Iterator[dict]:
        import csv
        with open(self.file_path, 'r') as f:
            reader = csv.DictReader(f, delimiter=self.delimiter)
            for row in reader:
                yield row
    
    def close(self) -> None:
        pass


class JSONSource(Source):
    """JSON文件数据源。"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def read(self) -> Iterator[dict]:
        import json
        with open(self.file_path, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                yield from data
            else:
                yield data
    
    def close(self) -> None:
        pass


class PostgresSource(Source):
    """PostgreSQL数据源。"""
    
    def __init__(self, connection_string: str, query: str):
        self.connection_string = connection_string
        self.query = query
    
    def read(self) -> Iterator[dict]:
        import psycopg2
        conn = psycopg2.connect(self.connection_string)
        cursor = conn.cursor()
        cursor.execute(self.query)
        columns = [desc[0] for desc in cursor.description]
        for row in cursor.fetchall():
            yield dict(zip(columns, row))
        cursor.close()
        conn.close()
    
    def close(self) -> None:
        pass