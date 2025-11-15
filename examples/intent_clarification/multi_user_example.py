"""
多用户场景使用示例

演示如何在多用户场景下安全地使用意图识别与问题澄清Agent。
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
from deepagents import create_deep_agent
from deepagents.middleware import (
    FilesystemMiddleware,
    SubAgentMiddleware,
)

from middleware_v2 import (
    IntentClassificationMiddleware,
    WorkspacePathManager,
)
from prompts_v2 import get_orchestrator_prompt
from agents import ALL_SUBAGENTS
from tools import set_knowledge_base, MockKnowledgeBase, knowledge_retriever


# ==================== 会话管理器 ====================


class SessionManager:
    """
    会话管理器

    为每个用户维护独立的会话，确保多用户场景下的隔离。
    """

    def __init__(self, agent, max_age_hours: int = 24):
        """
        Args:
            agent: Agent实例
            max_age_hours: 会话最大存活时间（小时）
        """
        self.agent = agent
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.max_age = timedelta(hours=max_age_hours)

    def generate_thread_id(self, user_id: str) -> str:
        """
        生成唯一的thread ID

        Args:
            user_id: 用户ID

        Returns:
            thread_id格式: user-{user_id}-{random_hex}
        """
        return f"user-{user_id}-{uuid.uuid4().hex[:8]}"

    def get_or_create_session(self, user_id: str) -> Dict[str, Any]:
        """
        获取或创建用户会话

        Args:
            user_id: 用户ID

        Returns:
            会话信息字典
        """
        # 检查是否有现有会话
        if user_id in self.sessions:
            session = self.sessions[user_id]
            # 检查会话是否过期
            if self._is_session_expired(session):
                print(f"会话已过期，为用户 {user_id} 创建新会话")
                self.cleanup_session(user_id)
            else:
                # 更新最后活动时间
                session["last_activity"] = datetime.now()
                return session

        # 创建新会话
        thread_id = self.generate_thread_id(user_id)
        session = {
            "thread_id": thread_id,
            "user_id": user_id,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0,
        }
        self.sessions[user_id] = session
        print(f"为用户 {user_id} 创建新会话: {thread_id}")
        return session

    def _is_session_expired(self, session: Dict[str, Any]) -> bool:
        """检查会话是否过期"""
        return datetime.now() - session["last_activity"] > self.max_age

    def invoke(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        为特定用户调用agent

        Args:
            user_id: 用户ID
            message: 用户消息

        Returns:
            Agent的返回结果
        """
        session = self.get_or_create_session(user_id)
        thread_id = session["thread_id"]

        # 构建配置
        config = {
            "configurable": {
                "thread_id": thread_id,
                "system_prompt": get_orchestrator_prompt(thread_id),
            }
        }

        # 调用agent
        print(f"\n[用户 {user_id}] 发送消息: {message}")
        print(f"[会话] {thread_id}")

        result = self.agent.invoke(
            {"messages": [("user", message)]},
            config=config,
        )

        # 更新会话统计
        session["message_count"] += 1
        session["last_activity"] = datetime.now()

        return result

    def get_response(self, user_id: str, message: str) -> str:
        """
        便捷方法：获取agent的文本响应

        Args:
            user_id: 用户ID
            message: 用户消息

        Returns:
            Agent的文本响应
        """
        result = self.invoke(user_id, message)
        if "messages" in result and len(result["messages"]) > 0:
            return result["messages"][-1].content
        return "抱歉，我无法理解您的问题。"

    def cleanup_session(self, user_id: str):
        """
        清理用户会话

        Args:
            user_id: 用户ID
        """
        if user_id in self.sessions:
            thread_id = self.sessions[user_id]["thread_id"]
            print(f"清理用户 {user_id} 的会话: {thread_id}")
            # TODO: 清理文件系统中的会话数据
            # workspace = WorkspacePathManager.get_thread_workspace(thread_id)
            # 删除 workspace 下的所有文件
            del self.sessions[user_id]

    def cleanup_expired_sessions(self):
        """清理所有过期会话"""
        expired_users = [
            user_id
            for user_id, session in self.sessions.items()
            if self._is_session_expired(session)
        ]

        for user_id in expired_users:
            self.cleanup_session(user_id)

        if expired_users:
            print(f"清理了 {len(expired_users)} 个过期会话")

    def get_session_info(self, user_id: str) -> Dict[str, Any] | None:
        """
        获取会话信息

        Args:
            user_id: 用户ID

        Returns:
            会话信息，如果不存在则返回None
        """
        return self.sessions.get(user_id)

    def list_active_sessions(self) -> list[Dict[str, Any]]:
        """列出所有活跃会话"""
        return [
            {
                "user_id": session["user_id"],
                "thread_id": session["thread_id"],
                "created_at": session["created_at"].isoformat(),
                "last_activity": session["last_activity"].isoformat(),
                "message_count": session["message_count"],
            }
            for session in self.sessions.values()
        ]


# ==================== 创建多用户安全的Agent ====================


def create_multi_user_agent():
    """
    创建支持多用户的agent

    Returns:
        编译后的agent
    """
    # 设置知识库
    set_knowledge_base(MockKnowledgeBase())

    # 创建agent（不设置固定的system_prompt）
    agent = create_deep_agent(
        model="claude-sonnet-4-5-20250929",
        # system_prompt会在调用时通过config动态设置
        middleware=[
            IntentClassificationMiddleware(),
            FilesystemMiddleware(),
            SubAgentMiddleware(
                subagents=ALL_SUBAGENTS,
                default_tools=[knowledge_retriever],
            ),
        ],
        tools=[knowledge_retriever],
    )

    return agent


# ==================== 示例场景 ====================


def example_concurrent_users():
    """示例：多个用户同时使用"""
    print("=" * 60)
    print("示例1: 多个用户同时使用")
    print("=" * 60)

    # 创建agent和会话管理器
    agent = create_multi_user_agent()
    manager = SessionManager(agent, max_age_hours=1)

    # 用户A的对话
    print("\n--- 用户A的对话 ---")
    response = manager.get_response("alice", "查询销售额")
    print(f"Agent: {response[:200]}...")

    # 用户B的对话（同时进行）
    print("\n--- 用户B的对话 ---")
    response = manager.get_response("bob", "统计活跃用户")
    print(f"Agent: {response[:200]}...")

    # 用户A继续对话
    print("\n--- 用户A继续对话 ---")
    response = manager.get_response("alice", "本月的")
    print(f"Agent: {response[:200]}...")
    # ✅ Agent能正确关联到Alice之前问的"销售额"

    # 用户C加入
    print("\n--- 用户C加入 ---")
    response = manager.get_response("charlie", "哪些商品卖得最好")
    print(f"Agent: {response[:200]}...")

    # 查看活跃会话
    print("\n--- 活跃会话 ---")
    sessions = manager.list_active_sessions()
    for session in sessions:
        print(f"用户: {session['user_id']}, 消息数: {session['message_count']}")


def example_session_isolation():
    """示例：验证会话隔离"""
    print("\n\n")
    print("=" * 60)
    print("示例2: 验证会话隔离")
    print("=" * 60)

    agent = create_multi_user_agent()
    manager = SessionManager(agent)

    # 两个用户问类似的问题
    print("\n用户A: 查询订单")
    manager.invoke("alice", "查询订单")

    print("\n用户B: 查询订单")
    manager.invoke("bob", "查询订单")

    # 检查它们使用的是不同的workspace
    alice_session = manager.get_session_info("alice")
    bob_session = manager.get_session_info("bob")

    alice_workspace = WorkspacePathManager.get_thread_workspace(
        alice_session["thread_id"]
    )
    bob_workspace = WorkspacePathManager.get_thread_workspace(
        bob_session["thread_id"]
    )

    print(f"\n✅ 会话隔离验证:")
    print(f"Alice的工作空间: {alice_workspace}")
    print(f"Bob的工作空间: {bob_workspace}")
    print(f"是否隔离: {alice_workspace != bob_workspace}")


def example_session_cleanup():
    """示例：会话清理"""
    print("\n\n")
    print("=" * 60)
    print("示例3: 会话清理")
    print("=" * 60)

    agent = create_multi_user_agent()
    # 设置较短的过期时间用于演示
    manager = SessionManager(agent, max_age_hours=0.001)  # 约3.6秒

    # 创建一些会话
    manager.invoke("alice", "查询销售额")
    manager.invoke("bob", "统计用户")

    print(f"\n当前活跃会话: {len(manager.sessions)}")

    # 等待会话过期
    print("等待会话过期...")
    import time

    time.sleep(4)

    # 清理过期会话
    manager.cleanup_expired_sessions()
    print(f"清理后活跃会话: {len(manager.sessions)}")


def example_workspace_paths():
    """示例：工作空间路径"""
    print("\n\n")
    print("=" * 60)
    print("示例4: 工作空间路径管理")
    print("=" * 60)

    thread_id = "user-alice-abc123"

    print(f"\nThread ID: {thread_id}\n")
    print("会话专属路径:")
    print(f"  工作空间: {WorkspacePathManager.get_thread_workspace(thread_id)}")
    print(f"  问题文件: {WorkspacePathManager.get_question_file(thread_id)}")
    print(f"  意图文件: {WorkspacePathManager.get_intent_file(thread_id)}")
    print(
        f"  澄清上下文: {WorkspacePathManager.get_clarification_context_file(thread_id)}"
    )
    print(
        f"  澄清后问题: {WorkspacePathManager.get_clarified_question_file(thread_id)}"
    )
    print(f"  结果文件: {WorkspacePathManager.get_result_file(thread_id)}")

    print("\n不同用户的路径是隔离的:")
    thread_id_bob = "user-bob-xyz789"
    print(f"  Alice: {WorkspacePathManager.get_intent_file(thread_id)}")
    print(f"  Bob:   {WorkspacePathManager.get_intent_file(thread_id_bob)}")


# ==================== Web应用示例（伪代码） ====================


def example_web_app_integration():
    """示例：Web应用集成"""
    print("\n\n")
    print("=" * 60)
    print("示例5: Web应用集成（伪代码）")
    print("=" * 60)

    print("""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# 全局agent和会话管理器
agent = create_multi_user_agent()
session_manager = SessionManager(agent)


class QueryRequest(BaseModel):
    user_id: str
    message: str


@app.post("/query")
async def query(request: QueryRequest):
    try:
        response = session_manager.get_response(
            request.user_id,
            request.message
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions")
async def list_sessions():
    return session_manager.list_active_sessions()


@app.delete("/session/{user_id}")
async def cleanup(user_id: str):
    session_manager.cleanup_session(user_id)
    return {"message": "Session cleaned up"}


# 定期清理任务
import asyncio

async def cleanup_task():
    while True:
        await asyncio.sleep(3600)  # 每小时
        session_manager.cleanup_expired_sessions()

asyncio.create_task(cleanup_task())
    """)


# ==================== 主函数 ====================


def main():
    """运行所有示例"""
    examples = [
        ("多个用户同时使用", example_concurrent_users),
        ("验证会话隔离", example_session_isolation),
        ("会话清理", example_session_cleanup),
        ("工作空间路径管理", example_workspace_paths),
        ("Web应用集成", example_web_app_integration),
    ]

    import sys

    if len(sys.argv) > 1:
        # 运行指定的示例
        example_num = int(sys.argv[1])
        if 1 <= example_num <= len(examples):
            name, func = examples[example_num - 1]
            print(f"\n运行示例: {name}\n")
            func()
        else:
            print(f"示例编号必须在 1-{len(examples)} 之间")
    else:
        # 显示所有可用示例
        print("可用的示例:")
        print()
        for i, (name, _) in enumerate(examples, 1):
            print(f"  {i}. {name}")
        print()
        print("用法: python multi_user_example.py <示例编号>")
        print("例如: python multi_user_example.py 1")


if __name__ == "__main__":
    main()
