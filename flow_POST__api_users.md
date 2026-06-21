# API流程图

```mermaid
graph TD
    %% 样式定义
    classDef apiNode fill:#4CAF50,stroke:#388E3C,color:white
    classDef funcNode fill:#2196F3,stroke:#1565C0,color:white
    classDef dbNode fill:#FF9800,stroke:#EF6C00,color:white

    API_POST__api_users["🌐 POST /api/users"]:::apiNode
    API_POST__api_users_step0["📦 create_new_user\n创建新用户\n📁 app\main.py"]:::funcNode
    API_POST__api_users --> API_POST__api_users_step0
    API_POST__api_users_step1["📦 verify_token\n验证Token\n📁 app\auth.py"]:::funcNode
    API_POST__api_users_step0 --> API_POST__api_users_step1
    API_POST__api_users_step2["📦 create_user\n创建用户\n📁 app\database.py"]:::funcNode
    API_POST__api_users_step1 --> API_POST__api_users_step2
    API_POST__api_users_step3["📦 get_connection\n获取数据库连接\n📁 app\database.py"]:::funcNode
    API_POST__api_users_step2 --> API_POST__api_users_step3
    API_POST__api_users_step4["📦 hash_password\n加密密码\n📁 app\auth.py"]:::funcNode
    API_POST__api_users_step3 --> API_POST__api_users_step4
    API_POST__api_users_end["✅ 返回响应"]:::apiNode
    API_POST__api_users_step4 --> API_POST__api_users_end


```

## 使用方法

1. 复制上面的Mermaid代码
2. 打开 [Mermaid Live Editor](https://mermaid.live)
3. 粘贴代码即可查看流程图

或者安装 VS Code 的 Mermaid 插件直接预览。
