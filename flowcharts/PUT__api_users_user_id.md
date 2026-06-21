# PUT /api/users/{user_id} 流程图

```mermaid
graph TD
    %% 样式定义
    classDef apiNode fill:#4CAF50,stroke:#388E3C,color:white
    classDef funcNode fill:#2196F3,stroke:#1565C0,color:white
    classDef dbNode fill:#FF9800,stroke:#EF6C00,color:white

    API_PUT__api_users_user_id["🌐 PUT /api/users/{user_id}"]:::apiNode
    API_PUT__api_users_user_id_step0["📦 handler"]:::funcNode
    API_PUT__api_users_user_id --> API_PUT__api_users_user_id_step0
    API_PUT__api_users_user_id_end["✅ 返回响应"]:::apiNode
    API_PUT__api_users_user_id_step0 --> API_PUT__api_users_user_id_end


```
