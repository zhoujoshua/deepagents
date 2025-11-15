# 多用户场景使用指南

本指南说明如何在多用户场景下安全地使用意图识别与问题澄清Agent。

## 问题说明

原始设计使用固定路径（如 `/workspace/intent.json`），存在以下问题：

### ❌ 问题1：会话冲突

```python
# 用户A的会话
agent.invoke({"messages": [("user", "查询销售额")]})
# 写入 /workspace/intent.json

# 用户B的会话（同时进行）
agent.invoke({"messages": [("user", "统计用户数")]})
# 覆盖 /workspace/intent.json ⚠️

# 用户A的后续请求
agent.invoke({"messages": [("user", "本月的")]})
# 读取到的是用户B的intent ❌
```

### ❌ 问题2：数据泄露

用户A的澄清上下文可能被用户B读取到，造成数据泄露。

### ❌ 问题3：状态混乱

多个会话共享同一个文件空间，状态管理混乱。

## 解决方案

我们提供了**三个版本**的实现，适用于不同场景：

### 方案1：基于Thread ID的路径隔离（推荐用于生产环境）

使用LangGraph的thread_id机制，为每个会话分配独立的工作空间。

#### 实现

```python
from examples.intent_clarification.middleware_v2 import (
    IntentClassificationMiddleware,
    WorkspacePathManager,
)
from examples.intent_clarification.prompts_v2 import get_orchestrator_prompt

# 创建agent时，prompt基于thread_id动态生成
def create_multi_user_safe_agent():
    return create_deep_agent(
        model="claude-sonnet-4-5-20250929",
        # 不使用固定prompt，而是在调用时动态生成
        system_prompt="",  # 占位
        middleware=[
            IntentClassificationMiddleware(),
            FilesystemMiddleware(),
            SubAgentMiddleware(...),
        ],
    )
```

#### 使用

```python
agent = create_multi_user_safe_agent()

# 用户A的会话
user_a_config = {
    "configurable": {
        "thread_id": "user-a-session-123",
        "system_prompt": get_orchestrator_prompt("user-a-session-123"),
    }
}

result_a = agent.invoke(
    {"messages": [("user", "查询销售额")]},
    config=user_a_config,
)
# 文件保存到：/workspace/user-a-session-123/intent.json

# 用户B的会话（同时进行）
user_b_config = {
    "configurable": {
        "thread_id": "user-b-session-456",
        "system_prompt": get_orchestrator_prompt("user-b-session-456"),
    }
}

result_b = agent.invoke(
    {"messages": [("user", "统计用户数")]},
    config=user_b_config,
)
# 文件保存到：/workspace/user-b-session-456/intent.json
# ✅ 不会冲突！
```

#### 会话管理

```python
class SessionManager:
    """会话管理器"""

    def __init__(self, agent):
        self.agent = agent
        self.sessions = {}  # user_id -> session_data

    def get_or_create_session(self, user_id: str) -> dict:
        """获取或创建用户会话"""
        if user_id not in self.sessions:
            import uuid
            thread_id = f"user-{user_id}-{uuid.uuid4().hex[:8]}"
            self.sessions[user_id] = {
                "thread_id": thread_id,
                "created_at": datetime.now(),
                "message_count": 0,
            }
        return self.sessions[user_id]

    def invoke(self, user_id: str, message: str):
        """为特定用户调用agent"""
        session = self.get_or_create_session(user_id)
        thread_id = session["thread_id"]

        config = {
            "configurable": {
                "thread_id": thread_id,
                "system_prompt": get_orchestrator_prompt(thread_id),
            }
        }

        result = self.agent.invoke(
            {"messages": [("user", message)]},
            config=config,
        )

        session["message_count"] += 1
        return result

    def cleanup_session(self, user_id: str):
        """清理用户会话"""
        if user_id in self.sessions:
            # 可以在这里清理文件系统中的会话数据
            del self.sessions[user_id]


# 使用示例
manager = SessionManager(agent)

# 多个用户同时使用
result1 = manager.invoke("alice", "查询销售额")
result2 = manager.invoke("bob", "统计用户数")
result3 = manager.invoke("alice", "本月的")  # Alice的后续对话
# ✅ 完全隔离，互不干扰
```

### 方案2：使用状态字段而非文件（推荐用于简单场景）

不使用文件系统存储意图等信息，而是直接使用状态字段。

#### 优点

- 更简单，不需要管理文件路径
- LangGraph自动处理状态隔离
- 适合不需要持久化的场景

#### 缺点

- 失去了"文件系统作为上下文卸载"的优势
- 大量数据会导致状态膨胀

#### 实现

```python
# 定义状态schema
from typing import TypedDict

class AgentState(TypedDict):
    messages: list
    intent: str | None
    needs_clarification: bool
    clarification_context: dict
    # ... 其他字段

# 创建agent时指定state schema
agent = create_deep_agent(
    state_schema=AgentState,
    # ...
)

# 使用时，每个用户有独立的state
config_a = {"configurable": {"thread_id": "user-a"}}
config_b = {"configurable": {"thread_id": "user-b"}}

# LangGraph自动隔离state
result_a = agent.invoke({"messages": [...]}, config=config_a)
result_b = agent.invoke({"messages": [...]}, config=config_b)
```

### 方案3：混合方案（推荐用于复杂场景）

结合方案1和方案2的优点：
- 小数据（如intent、status）存储在state
- 大数据（如knowledge_base结果、长上下文）存储在thread-specific文件

#### 实现

```python
class HybridState(TypedDict):
    messages: list
    # 小数据直接存state
    intent: str | None
    needs_clarification: bool
    # 大数据的文件路径
    knowledge_cache_file: str | None
    clarification_context_file: str | None


def create_hybrid_agent():
    return create_deep_agent(
        state_schema=HybridState,
        middleware=[
            IntentClassificationMiddleware(),  # 设置state.intent
            FilesystemMiddleware(),  # 处理大文件
            # ...
        ],
    )
```

## Web应用集成示例

### FastAPI示例

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI()

# 全局agent实例
agent = create_multi_user_safe_agent()

# 会话存储（生产环境应使用Redis等）
sessions = {}


class QueryRequest(BaseModel):
    user_id: str
    message: str


class QueryResponse(BaseModel):
    response: str
    session_id: str
    needs_input: bool


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """处理用户查询"""

    # 获取或创建会话
    if request.user_id not in sessions:
        thread_id = f"user-{request.user_id}-{uuid.uuid4().hex[:8]}"
        sessions[request.user_id] = {
            "thread_id": thread_id,
            "messages": [],
        }

    session = sessions[request.user_id]
    thread_id = session["thread_id"]

    # 构建配置
    config = {
        "configurable": {
            "thread_id": thread_id,
            "system_prompt": get_orchestrator_prompt(thread_id),
        }
    }

    # 调用agent
    result = agent.invoke(
        {"messages": [("user", request.message)]},
        config=config,
    )

    # 提取响应
    response_message = result["messages"][-1].content

    # 判断是否需要用户继续输入
    needs_input = "请问" in response_message or "？" in response_message

    return QueryResponse(
        response=response_message,
        session_id=thread_id,
        needs_input=needs_input,
    )


@app.delete("/session/{user_id}")
async def cleanup_session(user_id: str):
    """清理用户会话"""
    if user_id in sessions:
        # TODO: 清理文件系统中的会话数据
        del sessions[user_id]
        return {"message": "Session cleaned up"}
    raise HTTPException(status_code=404, detail="Session not found")
```

### 使用示例

```bash
# 用户A的请求
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "message": "查询销售额"}'

# 用户B的请求（同时进行）
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"user_id": "bob", "message": "统计用户数"}'

# 用户A的后续请求
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "message": "本月的"}'
```

## 持久化和清理

### 使用Checkpointer持久化会话

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# 使用SQLite持久化会话状态
checkpointer = SqliteSaver.from_conn_string("sessions.db")

agent = create_deep_agent(
    # ...
    checkpointer=checkpointer,
)

# 会话会自动持久化到数据库
# 服务重启后，会话可以恢复
```

### 定期清理过期会话

```python
import asyncio
from datetime import datetime, timedelta


class SessionCleaner:
    def __init__(self, session_manager, max_age_hours=24):
        self.session_manager = session_manager
        self.max_age = timedelta(hours=max_age_hours)

    async def cleanup_loop(self):
        """定期清理过期会话"""
        while True:
            await asyncio.sleep(3600)  # 每小时检查一次
            self.cleanup_expired_sessions()

    def cleanup_expired_sessions(self):
        """清理过期会话"""
        now = datetime.now()
        expired_users = []

        for user_id, session in self.session_manager.sessions.items():
            if now - session["created_at"] > self.max_age:
                expired_users.append(user_id)

        for user_id in expired_users:
            print(f"Cleaning up expired session for user {user_id}")
            self.session_manager.cleanup_session(user_id)

        print(f"Cleaned up {len(expired_users)} expired sessions")


# 启动清理任务
cleaner = SessionCleaner(manager)
asyncio.create_task(cleaner.cleanup_loop())
```

## 最佳实践

### 1. 始终使用Thread ID

```python
# ✅ 好的做法
config = {"configurable": {"thread_id": f"user-{user_id}-{session_id}"}}
agent.invoke(input, config=config)

# ❌ 不好的做法
agent.invoke(input)  # 使用默认thread，会冲突
```

### 2. 生成唯一的Thread ID

```python
import uuid

def generate_thread_id(user_id: str) -> str:
    """生成唯一的thread ID"""
    return f"user-{user_id}-{uuid.uuid4().hex[:8]}"

# 或者使用时间戳
def generate_thread_id_with_timestamp(user_id: str) -> str:
    """生成带时间戳的thread ID"""
    timestamp = int(datetime.now().timestamp())
    return f"user-{user_id}-{timestamp}"
```

### 3. 使用WorkspacePathManager获取路径

```python
from examples.intent_clarification.middleware_v2 import WorkspacePathManager

# ✅ 好的做法
thread_id = "user-alice-abc123"
intent_file = WorkspacePathManager.get_intent_file(thread_id)
# 返回: /workspace/user-alice-abc123/intent.json

# ❌ 不好的做法
intent_file = "/workspace/intent.json"  # 固定路径，会冲突
```

### 4. 在Prompt中使用动态路径

```python
# ✅ 好的做法
def get_prompt(thread_id: str) -> str:
    workspace = WorkspacePathManager.get_thread_workspace(thread_id)
    return f"请将结果保存到 {workspace}/result.json"

# ❌ 不好的做法
prompt = "请将结果保存到 /workspace/result.json"  # 固定路径
```

### 5. 实现会话超时和清理

```python
class Session:
    def __init__(self, thread_id: str, timeout_minutes: int = 30):
        self.thread_id = thread_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.timeout = timedelta(minutes=timeout_minutes)

    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return datetime.now() - self.last_activity > self.timeout

    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = datetime.now()
```

## 迁移指南

如果你已经使用了原始版本，如何迁移到多用户安全版本？

### 步骤1：更新导入

```python
# 旧的导入
from examples.intent_clarification.middleware import IntentClassificationMiddleware
from examples.intent_clarification.prompts import ORCHESTRATOR_PROMPT

# 新的导入
from examples.intent_clarification.middleware_v2 import IntentClassificationMiddleware
from examples.intent_clarification.prompts_v2 import get_orchestrator_prompt
```

### 步骤2：更新Agent创建

```python
# 旧的方式
agent = create_intent_clarification_agent()

# 新的方式
def create_agent_for_user(user_id: str):
    thread_id = generate_thread_id(user_id)
    return create_deep_agent(
        system_prompt=get_orchestrator_prompt(thread_id),
        middleware=[...],
    )
```

### 步骤3：更新调用方式

```python
# 旧的方式
result = agent.invoke({"messages": [("user", question)]})

# 新的方式
config = {"configurable": {"thread_id": thread_id}}
result = agent.invoke({"messages": [("user", question)]}, config=config)
```

## 总结

| 方案 | 适用场景 | 优点 | 缺点 |
|-----|---------|------|------|
| Thread ID路径隔离 | 生产环境、多用户SaaS | 完全隔离、支持持久化 | 需要管理thread_id |
| 状态字段 | 简单应用、单用户 | 简单直接 | 状态可能膨胀 |
| 混合方案 | 复杂应用、大数据 | 兼顾性能和隔离 | 实现稍复杂 |

**推荐**：生产环境使用**Thread ID路径隔离**方案，配合持久化和会话管理。
