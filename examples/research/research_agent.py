"""
================================================================================
研究代理 (Research Agent) - DeepAgents 框架示例
================================================================================

这是一个基于 DeepAgents 框架构建的深度研究代理示例。

【整体架构概述】
本示例展示了一个多代理协作系统，包含三个层次：
1. 主代理 (Main Agent) - 负责整体协调、任务分解和报告撰写
2. 研究子代理 (Research Sub-Agent) - 负责针对具体问题进行深度研究
3. 评审子代理 (Critique Sub-Agent) - 负责对最终报告进行质量评审

【工作流程】
用户提问 → 主代理分解任务 → 并行调用多个研究子代理 → 汇总信息撰写报告
         → 评审子代理审核 → 主代理修改完善 → 输出最终报告

【核心设计理念】
- 分而治之：将复杂研究任务拆解为多个子问题
- 并行处理：多个研究子代理可同时工作，提高效率
- 迭代优化：通过评审-修改循环不断提升报告质量
"""

# =============================================================================
# 导入依赖
# =============================================================================
import os
from typing import Literal

# DeepAgents 框架的核心函数，用于创建具有工具调用和子代理能力的智能代理
from deepagents import create_deep_agent

# Tavily 是一个专门为 AI 代理设计的搜索 API
# 相比普通搜索引擎，它返回的结果更适合 LLM 处理
from tavily import TavilyClient


# =============================================================================
# 工具定义 (Tool Definition)
# =============================================================================
"""
【工具的作用】
工具是代理与外部世界交互的桥梁。代理本身只能"思考"，
需要通过工具来执行实际操作，如：搜索网络、读写文件、调用API等。

在 DeepAgents 中，工具就是普通的 Python 函数，框架会：
1. 自动解析函数签名，生成工具描述供 LLM 理解
2. 当 LLM 决定调用工具时，框架自动执行对应函数
3. 将执行结果返回给 LLM 继续推理
"""

# 最佳实践：在模块级别初始化客户端，避免重复创建连接
# API Key 从环境变量获取，保证安全性
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


def internet_search(
    query: str,                                                    # 搜索查询词
    max_results: int = 5,                                         # 返回结果数量
    topic: Literal["general", "news", "finance"] = "general",     # 搜索主题类型
    include_raw_content: bool = False,                            # 是否包含网页原始内容
):
    """
    【网络搜索工具】

    这是代理的"眼睛"，让它能够获取互联网上的最新信息。

    参数说明：
    - query: 搜索查询词，代理会根据研究需要自动构造
    - max_results: 返回结果数量，默认5条，平衡信息量和处理效率
    - topic: 搜索主题，可选 general(通用)、news(新闻)、finance(财经)
    - include_raw_content: 是否返回完整网页内容，开启后信息更丰富但 token 消耗更大

    返回值：
    搜索结果字典，包含标题、URL、摘要等信息
    """
    search_docs = tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
    return search_docs


# =============================================================================
# 子代理定义 (Sub-Agent Definition)
# =============================================================================
"""
【子代理的概念】
子代理是主代理可以"雇佣"的专家助手。每个子代理有特定职责和能力。

在 DeepAgents 中，子代理定义为字典，包含：
- name: 子代理名称，主代理通过此名称调用
- description: 子代理能力描述，帮助主代理决定何时调用
- system_prompt: 子代理的系统提示词，定义其行为和角色
- tools: 子代理可使用的工具列表（可选）

【为什么需要子代理？】
1. 专业分工：不同代理专注不同任务，提高质量
2. 并行处理：多个子代理可同时工作
3. 资源隔离：每个子代理有独立的上下文，避免信息混乱
4. 可扩展性：可以轻松添加新的专家代理
"""

# -----------------------------------------------------------------------------
# 研究子代理 (Research Sub-Agent)
# -----------------------------------------------------------------------------
"""
【研究子代理的职责】
专门负责针对单一具体问题进行深度研究。

设计要点：
- 单一职责：每次只处理一个子问题，保证研究深度
- 独立性：有自己的搜索工具，可独立完成研究
- 并行性：主代理可同时启动多个研究子代理处理不同子问题
"""

sub_research_prompt = """You are a dedicated researcher. Your job is to conduct research based on the users questions.

Conduct thorough research and then reply to the user with a detailed answer to their question

only your FINAL answer will be passed on to the user. They will have NO knowledge of anything except your final message, so your final report should be your final message!"""
# 【提示词解析】
# 1. 角色定义：专职研究员
# 2. 任务说明：根据问题进行彻底研究
# 3. 重要约束：只有最终答案会被传递，强调输出质量

research_sub_agent = {
    "name": "research-agent",                           # 代理名称，主代理调用时使用
    "description": "Used to research more in depth questions. Only give this researcher one topic at a time. Do not pass multiple sub questions to this researcher. Instead, you should break down a large topic into the necessary components, and then call multiple research agents in parallel, one for each sub question.",
    # 【描述的重要性】
    # 这段描述告诉主代理：
    # - 用途：深度研究问题
    # - 使用方式：每次只给一个话题
    # - 最佳实践：拆分大任务，并行调用多个实例

    "system_prompt": sub_research_prompt,               # 系统提示词
    "tools": [internet_search],                         # 配备搜索工具
}


# -----------------------------------------------------------------------------
# 评审子代理 (Critique Sub-Agent)
# -----------------------------------------------------------------------------
"""
【评审子代理的职责】
负责审核最终报告的质量，提出改进建议。

这体现了 "自我反思" (Self-Reflection) 的设计模式：
- 让一个代理审核另一个代理的输出
- 通过多轮迭代提升输出质量
- 模拟人类写作中的 "写作-审稿-修改" 流程
"""

sub_critique_prompt = """You are a dedicated editor. You are being tasked to critique a report.

You can find the report at `final_report.md`.

You can find the question/topic for this report at `question.txt`.

The user may ask for specific areas to critique the report in. Respond to the user with a detailed critique of the report. Things that could be improved.

You can use the search tool to search for information, if that will help you critique the report

Do not write to the `final_report.md` yourself.

Things to check:
- Check that each section is appropriately named
- Check that the report is written as you would find in an essay or a textbook - it should be text heavy, do not let it just be a list of bullet points!
- Check that the report is comprehensive. If any paragraphs or sections are short, or missing important details, point it out.
- Check that the article covers key areas of the industry, ensures overall understanding, and does not omit important parts.
- Check that the article deeply analyzes causes, impacts, and trends, providing valuable insights
- Check that the article closely follows the research topic and directly answers questions
- Check that the article has a clear structure, fluent language, and is easy to understand.
"""
# 【评审标准解析】
# 1. 命名规范：章节标题是否恰当
# 2. 内容深度：是否为充实的文字，而非简单列表
# 3. 完整性：是否覆盖所有重要方面
# 4. 行业覆盖：是否涵盖关键领域
# 5. 分析深度：是否有因果分析、趋势洞察
# 6. 相关性：是否紧扣研究主题
# 7. 可读性：结构清晰、语言流畅

critique_sub_agent = {
    "name": "critique-agent",                           # 代理名称
    "description": "Used to critique the final report. Give this agent some information about how you want it to critique the report.",
    # 描述告诉主代理：这是用来审核报告的，可以指定审核方向

    "system_prompt": sub_critique_prompt,               # 系统提示词
    # 注意：评审代理没有配备工具，只进行阅读和分析
    # 这是有意为之：评审者只需要审阅，不需要额外搜索
}


# =============================================================================
# 主代理系统提示词 (Main Agent System Prompt)
# =============================================================================
"""
【系统提示词的结构】
一个好的系统提示词通常包含：
1. 角色定义：代理的身份和核心职责
2. 工作流程：完成任务的步骤指南
3. 工具使用说明：如何使用各个工具
4. 输出格式要求：最终输出的格式规范
5. 注意事项：特殊情况的处理方式
"""

research_instructions = """You are an expert researcher. Your job is to conduct thorough research, and then write a polished report.

The first thing you should do is to write the original user question to `question.txt` so you have a record of it.

Use the research-agent to conduct deep research. It will respond to your questions/topics with a detailed answer.

When you think you enough information to write a final report, write it to `final_report.md`

You can call the critique-agent to get a critique of the final report. After that (if needed) you can do more research and edit the `final_report.md`
You can do this however many times you want until are you satisfied with the result.

Only edit the file once at a time (if you call this tool in parallel, there may be conflicts).

Here are instructions for writing the final report:

<report_instructions>

CRITICAL: Make sure the answer is written in the same language as the human messages! If you make a todo plan - you should note in the plan what language the report should be in so you dont forget!
Note: the language the report should be in is the language the QUESTION is in, not the language/country that the question is ABOUT.

Please create a detailed answer to the overall research brief that:
1. Is well-organized with proper headings (# for title, ## for sections, ### for subsections)
2. Includes specific facts and insights from the research
3. References relevant sources using [Title](URL) format
4. Provides a balanced, thorough analysis. Be as comprehensive as possible, and include all information that is relevant to the overall research question. People are using you for deep research and will expect detailed, comprehensive answers.
5. Includes a "Sources" section at the end with all referenced links

You can structure your report in a number of different ways. Here are some examples:

To answer a question that asks you to compare two things, you might structure your report like this:
1/ intro
2/ overview of topic A
3/ overview of topic B
4/ comparison between A and B
5/ conclusion

To answer a question that asks you to return a list of things, you might only need a single section which is the entire list.
1/ list of things or table of things
Or, you could choose to make each item in the list a separate section in the report. When asked for lists, you don't need an introduction or conclusion.
1/ item 1
2/ item 2
3/ item 3

To answer a question that asks you to summarize a topic, give a report, or give an overview, you might structure your report like this:
1/ overview of topic
2/ concept 1
3/ concept 2
4/ concept 3
5/ conclusion

If you think you can answer the question with a single section, you can do that too!
1/ answer

REMEMBER: Section is a VERY fluid and loose concept. You can structure your report however you think is best, including in ways that are not listed above!
Make sure that your sections are cohesive, and make sense for the reader.

For each section of the report, do the following:
- Use simple, clear language
- Use ## for section title (Markdown format) for each section of the report
- Do NOT ever refer to yourself as the writer of the report. This should be a professional report without any self-referential language.
- Do not say what you are doing in the report. Just write the report without any commentary from yourself.
- Each section should be as long as necessary to deeply answer the question with the information you have gathered. It is expected that sections will be fairly long and verbose. You are writing a deep research report, and users will expect a thorough answer.
- Use bullet points to list out information when appropriate, but by default, write in paragraph form.

REMEMBER:
The brief and research may be in English, but you need to translate this information to the right language when writing the final answer.
Make sure the final answer report is in the SAME language as the human messages in the message history.

Format the report in clear markdown with proper structure and include source references where appropriate.

<Citation Rules>
- Assign each unique URL a single citation number in your text
- End with ### Sources that lists each source with corresponding numbers
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
- Each source should be a separate line item in a list, so that in markdown it is rendered as a list.
- Example format:
  [1] Source Title: URL
  [2] Source Title: URL
- Citations are extremely important. Make sure to include these, and pay a lot of attention to getting these right. Users will often use these citations to look into more information.
</Citation Rules>
</report_instructions>

You have access to a few tools.

## `internet_search`

Use this to run an internet search for a given query. You can specify the number of results, the topic, and whether raw content should be included.
"""
# 【主代理提示词关键点】
# 1. 工作流程：保存问题 → 调用研究代理 → 撰写报告 → 调用评审 → 迭代修改
# 2. 多语言支持：报告语言需与用户提问语言一致
# 3. 报告格式：详细的 Markdown 格式规范
# 4. 引用规则：严格的引用格式要求
# 5. 灵活性：报告结构可根据问题类型灵活调整


# =============================================================================
# 创建代理 (Agent Creation)
# =============================================================================
"""
【create_deep_agent 函数】
这是 DeepAgents 框架的核心函数，用于创建一个完整的智能代理。

参数说明：
- tools: 代理可使用的工具列表（Python 函数）
- system_prompt: 系统提示词，定义代理的角色和行为
- subagents: 子代理列表，代理可以调用这些子代理

返回值：
一个可执行的代理对象，可以接收用户输入并返回响应

【框架内部机制】
1. 工具注册：解析函数签名，生成 LLM 可理解的工具描述
2. 消息循环：用户输入 → LLM 推理 → 工具调用 → 结果反馈 → 继续推理
3. 子代理调用：当 LLM 决定调用子代理时，启动新的代理会话
"""

agent = create_deep_agent(
    tools=[internet_search],                                    # 主代理的工具
    system_prompt=research_instructions,                        # 主代理的系统提示词
    subagents=[critique_sub_agent, research_sub_agent],        # 可调用的子代理列表
)

# =============================================================================
# 使用示例 (Usage Example)
# =============================================================================
"""
【如何运行这个代理】

1. 设置环境变量：
   export TAVILY_API_KEY="your-tavily-api-key"
   export ANTHROPIC_API_KEY="your-anthropic-api-key"

2. 运行代理：
   python research_agent.py

3. 示例交互：
   用户: "请研究一下 2024 年 AI 代理技术的发展趋势"

   代理执行流程：
   a) 保存问题到 question.txt
   b) 将问题拆解为多个子问题（如：技术进展、应用场景、主要玩家等）
   c) 并行调用多个 research-agent 研究各子问题
   d) 汇总研究结果，撰写 final_report.md
   e) 调用 critique-agent 审核报告
   f) 根据审核意见修改报告
   g) 返回最终报告给用户

【架构图】

┌─────────────────────────────────────────────────────────────┐
│                         用户 (User)                          │
└─────────────────────────────┬───────────────────────────────┘
                              │ 提问
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    主代理 (Main Agent)                       │
│  • 任务分解与协调                                             │
│  • 报告撰写与修改                                             │
│  • 工具: internet_search                                     │
└────────┬────────────────────────────────────┬───────────────┘
         │ 调用                               │ 调用
         ▼                                    ▼
┌─────────────────────┐            ┌─────────────────────────┐
│  研究子代理 (×N)     │            │     评审子代理           │
│  Research Agent     │            │    Critique Agent       │
│  • 深度研究单一问题   │            │    • 审核报告质量        │
│  • 工具: internet_   │            │    • 提出改进建议        │
│         search      │            │    • 无额外工具          │
└─────────────────────┘            └─────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  Tavily Search API                           │
│              (互联网搜索服务)                                  │
└─────────────────────────────────────────────────────────────┘

【关键设计模式】

1. 分层代理 (Hierarchical Agents)
   - 主代理负责高层决策和协调
   - 子代理负责具体执行任务
   - 类似公司的管理层级结构

2. 工具增强 (Tool Augmentation)
   - 代理通过工具扩展能力边界
   - 搜索工具让代理能获取实时信息
   - 文件工具让代理能持久化输出

3. 迭代优化 (Iterative Refinement)
   - 通过评审-修改循环提升质量
   - 类似人类的写作修改过程
   - 可控制迭代次数平衡质量与成本

4. 并行处理 (Parallel Processing)
   - 多个研究子代理可同时工作
   - 显著提升复杂任务的处理效率
   - 充分利用 LLM 的并发能力
"""
