"""数据库操作模块"""

from typing import Optional, List
import sqlite3


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """初始化数据库"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_user(user_id: Optional[int] = None) -> Optional[dict]:
    """获取用户"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    else:
        cursor.execute("SELECT * FROM users")
    
    result = cursor.fetchall()
    conn.close()
    
    if user_id:
        return dict(result[0]) if result else None
    return [dict(row) for row in result]


def create_user(username: str, email: str, password: str) -> dict:
    """创建用户"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
        (username, email, password)
    )
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "id": user_id,
        "username": username,
        "email": email
    }


def update_user(user_id: int, username: str, email: str, password: str) -> dict:
    """更新用户"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET username = ?, email = ?, password = ? WHERE id = ?",
        (username, email, password, user_id)
    )
    
    conn.commit()
    conn.close()
    
    return {
        "id": user_id,
        "username": username,
        "email": email
    }


def delete_user(user_id: int) -> None:
    """删除用户"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    
    conn.commit()
    conn.close()
