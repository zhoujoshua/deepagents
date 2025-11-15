"""
基础测试

测试意图识别与问题澄清Agent的基本功能。
"""

import pytest
from unittest.mock import Mock, patch
from tools import MockKnowledgeBase, knowledge_retriever, set_knowledge_base
from agents import (
    clarification_subagent,
    sql_generator_subagent,
    get_agent_for_intent,
)


class TestKnowledgeBase:
    """测试知识库功能"""

    def setup_method(self):
        """每个测试前设置知识库"""
        set_knowledge_base(MockKnowledgeBase())

    def test_retrieve_schema(self):
        """测试检索schema"""
        result = knowledge_retriever("orders", "schema")
        assert "orders" in result.lower()
        assert "order_items" in result.lower() or "订单" in result

    def test_retrieve_business_rule(self):
        """测试检索业务规则"""
        result = knowledge_retriever("订单状态", "business_rule")
        assert "订单状态" in result or "status" in result.lower()

    def test_retrieve_example(self):
        """测试检索历史案例"""
        result = knowledge_retriever("销售额", "example")
        assert "sales" in result.lower() or "销售" in result
        assert "sql" in result.lower()

    def test_retrieve_all(self):
        """测试检索所有类型"""
        result = knowledge_retriever("订单", "all")
        # 应该包含多种类型的信息
        assert len(result) > 100  # 结果应该比较丰富


class TestAgentConfiguration:
    """测试Agent配置"""

    def test_clarification_subagent_config(self):
        """测试澄清agent配置"""
        assert clarification_subagent["name"] == "clarification-agent"
        assert "description" in clarification_subagent
        assert "system_prompt" in clarification_subagent
        assert "tools" in clarification_subagent
        assert knowledge_retriever in clarification_subagent["tools"]

    def test_sql_generator_subagent_config(self):
        """测试SQL生成agent配置"""
        assert sql_generator_subagent["name"] == "sql-generator"
        assert "description" in sql_generator_subagent
        assert "system_prompt" in sql_generator_subagent

    def test_intent_routing(self):
        """测试意图路由"""
        assert get_agent_for_intent("query_data") == "sql-generator"
        assert get_agent_for_intent("analyze_data") == "data-analyzer"
        assert get_agent_for_intent("unknown") is None


class TestPrompts:
    """测试Prompt定义"""

    def test_prompts_not_empty(self):
        """测试prompt不为空"""
        from prompts import (
            ORCHESTRATOR_PROMPT,
            INTENT_CLASSIFICATION_PROMPT,
            CLARIFICATION_AGENT_PROMPT,
            SQL_GENERATOR_AGENT_PROMPT,
        )

        assert len(ORCHESTRATOR_PROMPT) > 100
        assert len(INTENT_CLASSIFICATION_PROMPT) > 100
        assert len(CLARIFICATION_AGENT_PROMPT) > 100
        assert len(SQL_GENERATOR_AGENT_PROMPT) > 100

    def test_prompts_contain_key_concepts(self):
        """测试prompt包含关键概念"""
        from prompts import (
            ORCHESTRATOR_PROMPT,
            CLARIFICATION_AGENT_PROMPT,
            SQL_GENERATOR_AGENT_PROMPT,
        )

        # 主控制prompt应包含流程控制相关内容
        assert "意图" in ORCHESTRATOR_PROMPT or "intent" in ORCHESTRATOR_PROMPT.lower()
        assert "澄清" in ORCHESTRATOR_PROMPT or "clarif" in ORCHESTRATOR_PROMPT.lower()

        # 澄清prompt应包含多轮对话相关内容
        assert "澄清" in CLARIFICATION_AGENT_PROMPT or "clarif" in CLARIFICATION_AGENT_PROMPT.lower()
        assert "问题" in CLARIFICATION_AGENT_PROMPT or "question" in CLARIFICATION_AGENT_PROMPT.lower()

        # SQL生成prompt应包含SQL相关内容
        assert "SQL" in SQL_GENERATOR_AGENT_PROMPT.upper()
        assert "SELECT" in SQL_GENERATOR_AGENT_PROMPT or "查询" in SQL_GENERATOR_AGENT_PROMPT


class TestMiddleware:
    """测试中间件"""

    def test_intent_classification_middleware(self):
        """测试意图识别中间件"""
        from middleware import IntentClassificationMiddleware

        middleware = IntentClassificationMiddleware()
        assert middleware is not None
        assert hasattr(middleware, "__call__")

    def test_clarification_tracking_middleware(self):
        """测试澄清跟踪中间件"""
        from middleware import ClarificationTrackingMiddleware

        middleware = ClarificationTrackingMiddleware(max_clarification_rounds=5)
        assert middleware is not None
        assert middleware.max_rounds == 5

    def test_context_summary_middleware(self):
        """测试上下文总结中间件"""
        from middleware import ContextSummaryMiddleware

        middleware = ContextSummaryMiddleware(summarize_every_n_rounds=3)
        assert middleware is not None
        assert middleware.summarize_interval == 3


# ==================== 集成测试（需要实际的agent运行） ====================


class TestIntegration:
    """集成测试（可选，需要API key）"""

    @pytest.mark.skipif(
        True,  # 默认跳过，需要API key时手动运行
        reason="需要API key，手动运行时启用",
    )
    def test_create_agent(self):
        """测试创建agent"""
        from intent_clarification_agent import create_intent_clarification_agent

        set_knowledge_base(MockKnowledgeBase())

        agent = create_intent_clarification_agent()
        assert agent is not None

    @pytest.mark.skipif(
        True,
        reason="需要API key，手动运行时启用",
    )
    def test_simple_query(self):
        """测试简单查询"""
        from intent_clarification_agent import create_intent_clarification_agent

        set_knowledge_base(MockKnowledgeBase())

        agent = create_intent_clarification_agent()
        result = agent.invoke({"messages": [("user", "查询销售额")]})

        assert "messages" in result
        assert len(result["messages"]) > 0


# ==================== 运行测试 ====================

if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
