"""
知识库召回工具实现

提供多种知识库检索能力，包括数据库schema、业务规则、历史案例等。
"""

from typing import Literal, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# ==================== 知识库接口定义 ====================

class KnowledgeBase:
    """知识库基类，定义统一接口"""

    def retrieve_schema(self, query: str) -> dict[str, Any]:
        """检索数据库schema信息"""
        raise NotImplementedError

    def retrieve_business_rule(self, query: str) -> dict[str, Any]:
        """检索业务规则"""
        raise NotImplementedError

    def retrieve_example(self, query: str) -> dict[str, Any]:
        """检索历史案例"""
        raise NotImplementedError


# ==================== Mock实现（用于测试和演示） ====================

class MockKnowledgeBase(KnowledgeBase):
    """Mock知识库实现，用于测试和演示"""

    def __init__(self):
        # 模拟的数据库schema
        self.schemas = {
            "users": {
                "table_name": "users",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "username", "type": "VARCHAR(50)", "nullable": False},
                    {"name": "email", "type": "VARCHAR(100)", "nullable": False},
                    {"name": "created_at", "type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP"},
                    {"name": "last_login", "type": "TIMESTAMP", "nullable": True},
                ],
                "indexes": ["idx_username", "idx_email"],
            },
            "orders": {
                "table_name": "orders",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "user_id", "type": "INTEGER", "foreign_key": "users.id"},
                    {"name": "order_date", "type": "DATE", "nullable": False},
                    {"name": "total_amount", "type": "DECIMAL(10,2)", "nullable": False},
                    {"name": "status", "type": "VARCHAR(20)", "nullable": False},
                ],
                "indexes": ["idx_user_id", "idx_order_date", "idx_status"],
            },
            "order_items": {
                "table_name": "order_items",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "order_id", "type": "INTEGER", "foreign_key": "orders.id"},
                    {"name": "product_id", "type": "INTEGER", "foreign_key": "products.id"},
                    {"name": "quantity", "type": "INTEGER", "nullable": False},
                    {"name": "unit_price", "type": "DECIMAL(10,2)", "nullable": False},
                ],
            },
            "products": {
                "table_name": "products",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "name", "type": "VARCHAR(100)", "nullable": False},
                    {"name": "category", "type": "VARCHAR(50)", "nullable": False},
                    {"name": "price", "type": "DECIMAL(10,2)", "nullable": False},
                    {"name": "stock", "type": "INTEGER", "default": "0"},
                ],
            },
        }

        # 模拟的业务规则
        self.business_rules = {
            "订单状态": {
                "rule": "订单状态流转规则",
                "description": "订单状态包括：pending（待处理）、processing（处理中）、shipped（已发货）、delivered（已送达）、cancelled（已取消）",
                "constraints": [
                    "只能从pending转到processing或cancelled",
                    "只能从processing转到shipped或cancelled",
                    "只能从shipped转到delivered",
                    "cancelled是终态",
                ],
            },
            "销售统计": {
                "rule": "销售金额计算规则",
                "description": "销售金额 = SUM(order_items.quantity * order_items.unit_price)",
                "notes": ["不包括已取消的订单", "按order_date进行时间范围过滤"],
            },
            "活跃用户": {
                "rule": "活跃用户定义",
                "description": "在指定时间范围内有登录记录或下单记录的用户",
                "metrics": [
                    "日活跃用户(DAU): 最近1天有活动",
                    "周活跃用户(WAU): 最近7天有活动",
                    "月活跃用户(MAU): 最近30天有活动",
                ],
            },
        }

        # 模拟的历史案例
        self.examples = {
            "查询销售额": {
                "question": "查询2024年1月的总销售额",
                "clarified_question": "查询2024年1月1日至2024年1月31日期间，所有已完成订单（状态为delivered）的总销售金额",
                "sql": """
SELECT
    SUM(oi.quantity * oi.unit_price) as total_sales
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
WHERE o.order_date >= '2024-01-01'
  AND o.order_date < '2024-02-01'
  AND o.status = 'delivered'
                """.strip(),
            },
            "查询活跃用户": {
                "question": "最近一周有多少活跃用户",
                "clarified_question": "查询最近7天（从今天往前推7天）内有登录或下单行为的去重用户数量",
                "sql": """
SELECT COUNT(DISTINCT user_id) as active_users
FROM (
    SELECT user_id FROM users
    WHERE last_login >= CURRENT_DATE - INTERVAL '7 days'
    UNION
    SELECT user_id FROM orders
    WHERE order_date >= CURRENT_DATE - INTERVAL '7 days'
) as active_users_union
                """.strip(),
            },
            "商品销量排名": {
                "question": "哪些商品卖得最好",
                "clarified_question": "查询最近30天内，按销售数量排名前10的商品，显示商品名称、类别、销售数量和销售金额",
                "sql": """
SELECT
    p.name,
    p.category,
    SUM(oi.quantity) as total_quantity,
    SUM(oi.quantity * oi.unit_price) as total_revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.id
JOIN orders o ON oi.order_id = o.id
WHERE o.order_date >= CURRENT_DATE - INTERVAL '30 days'
  AND o.status != 'cancelled'
GROUP BY p.id, p.name, p.category
ORDER BY total_quantity DESC
LIMIT 10
                """.strip(),
            },
        }

    def retrieve_schema(self, query: str) -> dict[str, Any]:
        """检索schema信息"""
        # 简单的关键词匹配
        query_lower = query.lower()
        results = {}

        for table_name, schema_info in self.schemas.items():
            if table_name in query_lower or any(
                col["name"] in query_lower for col in schema_info["columns"]
            ):
                results[table_name] = schema_info

        # 如果没有匹配，返回所有表的概览
        if not results:
            results = {
                name: {
                    "table_name": name,
                    "columns": [col["name"] for col in info["columns"]],
                }
                for name, info in self.schemas.items()
            }

        return results

    def retrieve_business_rule(self, query: str) -> dict[str, Any]:
        """检索业务规则"""
        query_lower = query.lower()
        results = {}

        for rule_name, rule_info in self.business_rules.items():
            if (
                rule_name.lower() in query_lower
                or rule_info["description"].lower() in query_lower
                or any(keyword in query_lower for keyword in ["订单", "销售", "用户", "活跃"])
            ):
                results[rule_name] = rule_info

        return results

    def retrieve_example(self, query: str) -> dict[str, Any]:
        """检索历史案例"""
        query_lower = query.lower()
        results = {}

        for example_name, example_info in self.examples.items():
            if (
                any(
                    keyword in query_lower
                    for keyword in ["销售", "活跃", "商品", "排名", "用户"]
                )
                or example_name.lower() in query_lower
            ):
                results[example_name] = example_info

        return results


# ==================== 向量数据库实现（可选） ====================

class VectorKnowledgeBase(KnowledgeBase):
    """基于向量数据库的知识库实现（需要安装chromadb等依赖）"""

    def __init__(self, collection_name: str = "knowledge_base"):
        try:
            import chromadb
            from chromadb.config import Settings

            self.client = chromadb.Client(Settings(anonymized_telemetry=False))
            self.collection = self.client.get_or_create_collection(collection_name)
        except ImportError:
            raise ImportError(
                "VectorKnowledgeBase requires chromadb. Install it with: pip install chromadb"
            )

    def retrieve_schema(self, query: str) -> dict[str, Any]:
        results = self.collection.query(
            query_texts=[query], n_results=5, where={"type": "schema"}
        )
        return self._format_results(results)

    def retrieve_business_rule(self, query: str) -> dict[str, Any]:
        results = self.collection.query(
            query_texts=[query], n_results=5, where={"type": "business_rule"}
        )
        return self._format_results(results)

    def retrieve_example(self, query: str) -> dict[str, Any]:
        results = self.collection.query(
            query_texts=[query], n_results=3, where={"type": "example"}
        )
        return self._format_results(results)

    def _format_results(self, results: dict) -> dict[str, Any]:
        """格式化向量检索结果"""
        formatted = {}
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                formatted[f"result_{i+1}"] = {
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                }
        return formatted


# ==================== 全局知识库实例 ====================

# 默认使用Mock实现，可以在运行时替换
_knowledge_base = MockKnowledgeBase()


def set_knowledge_base(kb: KnowledgeBase):
    """设置全局知识库实例"""
    global _knowledge_base
    _knowledge_base = kb


def get_knowledge_base() -> KnowledgeBase:
    """获取全局知识库实例"""
    return _knowledge_base


# ==================== LangChain工具定义 ====================


@tool
def knowledge_retriever(
    query: str,
    knowledge_type: Literal["schema", "business_rule", "example", "all"] = "all",
) -> str:
    """
    从知识库中检索相关信息，帮助理解用户问题和生成准确的SQL。

    Args:
        query: 查询文本，描述你想要查找的信息
        knowledge_type: 知识类型
            - schema: 数据库表结构、字段定义、关系等
            - business_rule: 业务规则、指标定义、计算逻辑等
            - example: 历史案例、类似问题的SQL示例等
            - all: 所有类型（默认）

    Returns:
        检索到的相关信息，以结构化文本形式返回

    Examples:
        >>> knowledge_retriever("订单表有哪些字段", "schema")
        >>> knowledge_retriever("如何计算销售额", "business_rule")
        >>> knowledge_retriever("如何查询活跃用户", "example")
    """
    kb = get_knowledge_base()
    results = {}

    try:
        if knowledge_type in ("schema", "all"):
            schema_results = kb.retrieve_schema(query)
            if schema_results:
                results["schemas"] = schema_results

        if knowledge_type in ("business_rule", "all"):
            rule_results = kb.retrieve_business_rule(query)
            if rule_results:
                results["business_rules"] = rule_results

        if knowledge_type in ("example", "all"):
            example_results = kb.retrieve_example(query)
            if example_results:
                results["examples"] = example_results

        # 格式化输出
        if not results:
            return "没有找到相关信息。请尝试使用不同的关键词。"

        output_parts = []

        if "schemas" in results:
            output_parts.append("## 数据库Schema信息\n")
            for table_name, schema in results["schemas"].items():
                output_parts.append(f"\n### 表: {table_name}")
                output_parts.append(f"列:")
                for col in schema.get("columns", []):
                    col_def = f"  - {col['name']}: {col['type']}"
                    if col.get("primary_key"):
                        col_def += " [PRIMARY KEY]"
                    if col.get("foreign_key"):
                        col_def += f" [FK -> {col['foreign_key']}]"
                    if not col.get("nullable", True):
                        col_def += " [NOT NULL]"
                    output_parts.append(col_def)

        if "business_rules" in results:
            output_parts.append("\n## 业务规则\n")
            for rule_name, rule in results["business_rules"].items():
                output_parts.append(f"\n### {rule_name}")
                output_parts.append(f"说明: {rule['description']}")
                if "constraints" in rule:
                    output_parts.append("约束条件:")
                    for constraint in rule["constraints"]:
                        output_parts.append(f"  - {constraint}")
                if "metrics" in rule:
                    output_parts.append("指标定义:")
                    for metric in rule["metrics"]:
                        output_parts.append(f"  - {metric}")

        if "examples" in results:
            output_parts.append("\n## 历史案例\n")
            for example_name, example in results["examples"].items():
                output_parts.append(f"\n### {example_name}")
                output_parts.append(f"原始问题: {example['question']}")
                output_parts.append(f"澄清后: {example['clarified_question']}")
                output_parts.append(f"SQL:\n```sql\n{example['sql']}\n```")

        return "\n".join(output_parts)

    except Exception as e:
        return f"检索知识库时出错: {str(e)}"


# ==================== 辅助工具 ====================


@tool
def update_clarification_context(key: str, value: str) -> str:
    """
    更新澄清上下文，记录已收集的信息。

    这个工具用于在多轮澄清对话中，保存用户提供的信息，
    以便后续使用这些信息生成完整的查询。

    Args:
        key: 信息的键（如"时间范围"、"目标指标"等）
        value: 信息的值

    Returns:
        确认消息
    """
    # 实际实现中，这会写入文件系统或状态
    # 这里只是一个占位符
    return f"已记录: {key} = {value}"


@tool
def format_clarified_question(
    original_question: str, collected_info: dict[str, str]
) -> str:
    """
    基于原始问题和收集到的信息，生成澄清后的完整问题描述。

    Args:
        original_question: 用户的原始问题
        collected_info: 收集到的补充信息字典

    Returns:
        澄清后的完整问题描述
    """
    parts = [f"原始问题: {original_question}", "\n补充信息:"]
    for key, value in collected_info.items():
        parts.append(f"  - {key}: {value}")

    parts.append("\n完整描述:")
    # 这里可以使用LLM来生成更自然的描述
    # 暂时简单拼接
    clarified = original_question
    for key, value in collected_info.items():
        clarified += f"，{key}为{value}"

    parts.append(f"  {clarified}")
    return "\n".join(parts)


# ==================== 导出 ====================

__all__ = [
    "KnowledgeBase",
    "MockKnowledgeBase",
    "VectorKnowledgeBase",
    "set_knowledge_base",
    "get_knowledge_base",
    "knowledge_retriever",
    "update_clarification_context",
    "format_clarified_question",
]
