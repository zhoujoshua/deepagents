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

# =============================================================================
# 【研究子代理提示词 - 逐句深度解析】
# =============================================================================
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │ 第一句: "You are a dedicated researcher."                               │
# │ 译文: "你是一名专职研究员。"                                              │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ 【设计意图】                                                             │
# │ • 角色扮演 (Role-Playing): 让 LLM 进入特定角色心智模式                    │
# │ • "dedicated" 强调专注性，暗示不要偏离研究任务                            │
# │ • 简洁明了，一句话建立身份认同                                            │
# │                                                                         │
# │ 【提示词工程技巧】                                                        │
# │ 这是经典的 "角色设定" 技巧。研究表明，给 LLM 设定角色可以：                │
# │ 1. 激活相关知识领域                                                      │
# │ 2. 调整输出风格和语气                                                    │
# │ 3. 提高任务专注度                                                        │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │ 第二句: "Your job is to conduct research based on the users questions." │
# │ 译文: "你的工作是根据用户的问题进行研究。"                                  │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ 【设计意图】                                                             │
# │ • 明确核心职责：研究                                                     │
# │ • 输入来源：用户的问题（由主代理传递）                                     │
# │ • 建立任务边界：只做研究，不做其他事情                                     │
# │                                                                         │
# │ 【注意事项】                                                             │
# │ 这里的 "user" 实际上是主代理，而非最终用户                                │
# │ 子代理不直接与最终用户交互，而是接收主代理分配的任务                        │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │ 第三句: "Conduct thorough research and then reply to the user           │
# │         with a detailed answer to their question"                       │
# │ 译文: "进行彻底的研究，然后用详细的答案回复用户的问题。"                    │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ 【设计意图】                                                             │
# │ • "thorough" (彻底的): 强调研究深度，不要浅尝辄止                         │
# │ • "detailed" (详细的): 强调输出质量，不要敷衍了事                         │
# │ • 工作流程: 先研究 → 再回复（顺序很重要）                                 │
# │                                                                         │
# │ 【隐含期望】                                                             │
# │ 代理应该：                                                               │
# │ 1. 多次调用搜索工具获取信息                                               │
# │ 2. 综合多个来源的信息                                                    │
# │ 3. 组织成结构化的详细答案                                                │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │ 第四句: "only your FINAL answer will be passed on to the user.          │
# │         They will have NO knowledge of anything except your final       │
# │         message, so your final report should be your final message!"    │
# │ 译文: "只有你的最终答案会被传递给用户。他们对你的最终消息之外的任何内容       │
# │       都一无所知，所以你的最终报告应该就是你的最终消息！"                   │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ 【设计意图 - 这是最关键的一句！】                                         │
# │                                                                         │
# │ 问题背景：                                                               │
# │ 子代理可能会进行多轮对话（搜索→分析→再搜索...），但只有最后一条消息          │
# │ 会返回给主代理。如果子代理在过程中输出了答案，主代理看不到！                 │
# │                                                                         │
# │ 解决方案：                                                               │
# │ • 用大写 "FINAL" 和 "NO knowledge" 强调这个约束                          │
# │ • 告诉代理必须把所有研究成果压缩到最后一条消息中                           │
# │ • 使用感叹号增加紧迫感                                                   │
# │                                                                         │
# │ 【提示词工程技巧】                                                        │
# │ 这是 "输出格式约束" 的典型示例：                                          │
# │ 1. 解释系统限制（只有最终消息会被传递）                                    │
# │ 2. 解释后果（用户看不到其他内容）                                         │
# │ 3. 给出明确指示（最终报告 = 最终消息）                                    │
# └─────────────────────────────────────────────────────────────────────────┘
#
# 【总结：为什么这个提示词设计得好？】
# 1. 简短精炼：只有3句话，约60个单词，避免信息过载
# 2. 结构清晰：角色 → 任务 → 要求 → 约束
# 3. 重点突出：最关键的约束放在最后，用大写和感叹号强调
# 4. 目标明确：代理知道要做什么、怎么做、输出什么
#

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

# =============================================================================
# 【评审子代理提示词 - 逐段深度解析】
# =============================================================================
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │ 【第一部分：角色与任务定义】                                              │
# │ "You are a dedicated editor. You are being tasked to critique a report."│
# │ 译文: "你是一名专职编辑。你的任务是评审一份报告。"                          │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ 【设计意图】                                                             │
# │ • 角色选择 "editor"(编辑) 而非 "reviewer"(审稿人)                        │
# │   → 编辑更强调改进建议，审稿人可能只关注通过/拒绝                          │
# │ • "critique" 而非 "review"                                              │
# │   → critique 暗示深度分析和建设性批评                                    │
# │                                                                         │
# │ 【AI 代理设计哲学】                                                       │
# │ 评审代理体现了 "对抗性协作" 的设计思想：                                   │
# │ • 研究代理努力写出好报告                                                  │
# │ • 评审代理努力找出问题                                                   │
# │ • 两者的对抗产生更高质量的输出                                            │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │ 【第二部分：上下文信息】                                                  │
# │ "You can find the report at `final_report.md`."                         │
# │ "You can find the question/topic for this report at `question.txt`."    │
# │ 译文: "你可以在 final_report.md 找到报告，在 question.txt 找到研究问题。" │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ 【设计意图】                                                             │
# │ • 提供明确的文件路径，代理可以用文件读取工具获取内容                        │
# │ • 分离 "报告内容" 和 "原始问题"：                                         │
# │   → 报告内容：评审的对象                                                 │
# │   → 原始问题：评审的标准（报告是否回答了这个问题？）                        │
# │                                                                         │
# │ 【技术实现】                                                             │
# │ 代理会调用文件读取工具来获取这两个文件的内容                               │
# │ 这种设计让代理能够访问主代理产生的中间产物                                 │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │ 【第三部分：任务灵活性】                                                  │
# │ "The user may ask for specific areas to critique the report in."        │
# │ 译文: "用户可能会要求你针对特定方面来评审报告。"                           │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ 【设计意图】                                                             │
# │ • 允许主代理指定评审重点（如：只看引用格式、只看逻辑结构）                  │
# │ • 提供灵活性，避免每次都做全面评审（节省 token）                           │
# │ • 主代理可以根据之前的反馈，要求聚焦特定问题                               │
# │                                                                         │
# │ 【使用场景】                                                             │
# │ 主代理调用时可以说：                                                      │
# │ "请重点检查报告中的数据准确性"                                            │
# │ "请评审报告的结论部分是否有逻辑漏洞"                                      │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │ 【第四部分：权限约束】                                                    │
# │ "Do not write to the `final_report.md` yourself."                       │
# │ 译文: "不要自己写入 final_report.md。"                                   │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ 【设计意图 - 职责分离原则】                                               │
# │ • 评审代理只能"说"，不能"改"                                              │
# │ • 修改权保留给主代理，确保主代理对最终输出有控制权                          │
# │ • 避免多个代理同时修改同一文件导致冲突                                     │
# │                                                                         │
# │ 【类比】                                                                 │
# │ 就像论文审稿人只能给出修改意见，不能直接改论文                             │
# │ 作者（主代理）根据意见决定如何修改                                        │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │ 【第五部分：评审检查清单 - 7大评审维度】                                   │
# ├─────────────────────────────────────────────────────────────────────────┤
# │                                                                         │
# │ ① 命名规范 (Naming Convention)                                          │
# │    "Check that each section is appropriately named"                     │
# │    → 章节标题应准确反映内容                                              │
# │    → 避免模糊的标题如 "其他信息"                                         │
# │                                                                         │
# │ ② 内容形式 (Content Format)                                             │
# │    "written as you would find in an essay or a textbook"                │
# │    "should be text heavy, do not let it just be a list of bullet points"│
# │    → 要求段落式写作，而非简单的要点列表                                   │
# │    → 深度研究报告应该有论述、分析、解释                                   │
# │                                                                         │
# │ ③ 完整性 (Comprehensiveness)                                            │
# │    "If any paragraphs or sections are short, or missing important       │
# │     details, point it out"                                              │
# │    → 检查是否有遗漏的重要信息                                            │
# │    → 每个部分应该足够详尽                                                │
# │                                                                         │
# │ ④ 行业覆盖 (Industry Coverage)                                          │
# │    "covers key areas of the industry, ensures overall understanding,    │
# │     and does not omit important parts"                                  │
# │    → 从行业角度检查全面性                                                │
# │    → 确保关键领域都有涉及                                                │
# │                                                                         │
# │ ⑤ 分析深度 (Analysis Depth)                                             │
# │    "deeply analyzes causes, impacts, and trends, providing valuable     │
# │     insights"                                                           │
# │    → 不只是罗列事实，要有因果分析                                         │
# │    → 提供有价值的洞察和趋势判断                                          │
# │                                                                         │
# │ ⑥ 相关性 (Relevance)                                                    │
# │    "closely follows the research topic and directly answers questions"  │
# │    → 内容是否紧扣主题                                                    │
# │    → 是否直接回答了用户的问题                                            │
# │                                                                         │
# │ ⑦ 可读性 (Readability)                                                  │
# │    "clear structure, fluent language, and is easy to understand"        │
# │    → 结构清晰                                                           │
# │    → 语言流畅                                                           │
# │    → 易于理解                                                           │
# │                                                                         │
# └─────────────────────────────────────────────────────────────────────────┘
#
# 【总结：评审代理的设计亮点】
#
# 1. 【职责清晰】只评审不修改，保持架构清晰
# 2. 【标准明确】7个维度的检查清单，确保评审全面
# 3. 【灵活可控】支持聚焦特定方面，节省资源
# 4. 【可追溯】评审意见会返回给主代理，形成改进依据
#
# 【这体现的设计模式：Reflection Pattern (反思模式)】
#
#    ┌──────────┐     写报告      ┌──────────┐
#    │  主代理   │ ───────────→  │ 报告文件  │
#    └──────────┘                └──────────┘
#         ↑                            │
#         │ 改进建议                    │ 读取
#         │                            ↓
#    ┌──────────┐     评审意见    ┌──────────┐
#    │  主代理   │ ←─────────── │ 评审代理  │
#    └──────────┘                └──────────┘
#
# 这种 "生成-评审-修改" 的循环是提升 AI 输出质量的有效方法
#

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
# =============================================================================
# 【主代理系统提示词 - 完整深度解析】
# =============================================================================
#
# 这是整个系统中最复杂的提示词，包含约500个单词，结构如下：
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │                        主代理提示词结构总览                               │
# ├─────────────────────────────────────────────────────────────────────────┤
# │  1. 角色定义 (1句)                                                       │
# │  2. 工作流程 (5句)                                                       │
# │  3. 报告撰写指南 <report_instructions> (主体部分)                         │
# │     ├── 语言要求                                                        │
# │     ├── 内容要求 (5点)                                                  │
# │     ├── 报告结构模板 (4种类型)                                           │
# │     ├── 写作规范 (6点)                                                  │
# │     └── 引用规则 <Citation Rules>                                       │
# │  4. 工具说明 (1段)                                                       │
# └─────────────────────────────────────────────────────────────────────────┘
#
# =============================================================================
# 【第一部分：角色定义】
# =============================================================================
# "You are an expert researcher. Your job is to conduct thorough research,
#  and then write a polished report."
#
# 【解析】
# • "expert researcher" - 专家级研究员，暗示高质量输出
# • "thorough research" - 彻底研究，不能敷衍
# • "polished report" - 精心撰写的报告，强调最终输出的质量
#
# =============================================================================
# 【第二部分：工作流程 - 5个关键步骤】
# =============================================================================
#
# ┌─ 步骤1 ─────────────────────────────────────────────────────────────────┐
# │ "The first thing you should do is to write the original user question   │
# │  to `question.txt` so you have a record of it."                         │
# │                                                                         │
# │ 【为什么要保存问题？】                                                    │
# │ • 创建任务上下文的持久化记录                                              │
# │ • 评审代理需要读取这个文件来判断报告是否切题                               │
# │ • 避免在长对话中遗忘原始目标                                              │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─ 步骤2 ─────────────────────────────────────────────────────────────────┐
# │ "Use the research-agent to conduct deep research. It will respond to    │
# │  your questions/topics with a detailed answer."                         │
# │                                                                         │
# │ 【设计意图】                                                             │
# │ • 明确指出要使用 research-agent 子代理                                   │
# │ • 告诉主代理子代理会返回什么（详细答案）                                   │
# │ • 主代理应该拆分问题，多次调用研究子代理                                   │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─ 步骤3 ─────────────────────────────────────────────────────────────────┐
# │ "When you think you enough information to write a final report,         │
# │  write it to `final_report.md`"                                         │
# │                                                                         │
# │ 【设计意图】                                                             │
# │ • 主代理自行判断何时信息足够（自主决策）                                   │
# │ • 输出到固定文件路径，方便评审代理读取                                     │
# │ • 使用 Markdown 格式，便于渲染和阅读                                      │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─ 步骤4 ─────────────────────────────────────────────────────────────────┐
# │ "You can call the critique-agent to get a critique of the final report. │
# │  After that (if needed) you can do more research and edit the           │
# │  `final_report.md`"                                                     │
# │                                                                         │
# │ 【迭代优化机制】                                                         │
# │ • 评审是可选的（"can call"），主代理可以决定是否需要                       │
# │ • 评审后可以：1) 做更多研究  2) 直接修改报告                              │
# │ • 形成闭环：写→评→改→再评...                                            │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─ 步骤5 ─────────────────────────────────────────────────────────────────┐
# │ "You can do this however many times you want until are you satisfied    │
# │  with the result."                                                      │
# │                                                                         │
# │ 【设计意图】                                                             │
# │ • 迭代次数不固定，由代理自己决定                                          │
# │ • "satisfied" 是终止条件，需要代理自我评估                                │
# │ • 平衡质量和成本：太多迭代浪费 token，太少可能质量不够                      │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─ 并发控制 ──────────────────────────────────────────────────────────────┐
# │ "Only edit the file once at a time (if you call this tool in parallel,  │
# │  there may be conflicts)."                                              │
# │                                                                         │
# │ 【技术细节】                                                             │
# │ • LLM 可能会并行调用多个工具（parallel tool calls）                       │
# │ • 如果同时编辑同一文件，会产生冲突                                        │
# │ • 这是给代理的技术约束，避免运行时错误                                     │
# └─────────────────────────────────────────────────────────────────────────┘
#
# =============================================================================
# 【第三部分：报告撰写指南 <report_instructions>】
# =============================================================================
#
# ┌─ 语言要求 (最重要！) ────────────────────────────────────────────────────┐
# │ "CRITICAL: Make sure the answer is written in the same language as      │
# │  the human messages!"                                                   │
# │                                                                         │
# │ 【为什么用 CRITICAL？】                                                  │
# │ • 这是最容易出错的地方！                                                  │
# │ • 研究材料通常是英文，但用户可能用中文提问                                 │
# │ • 代理容易"偷懒"直接用英文写报告                                          │
# │ • 大写 + 感叹号 = 最高优先级约束                                          │
# │                                                                         │
# │ "the language the report should be in is the language the QUESTION      │
# │  is in, not the language/country that the question is ABOUT."           │
# │                                                                         │
# │ 【澄清边界情况】                                                         │
# │ 例如：用中文问 "研究一下美国的AI政策"                                     │
# │ • 问题语言 = 中文 ✓                                                     │
# │ • 问题主题 = 美国（英语国家）✗                                           │
# │ • 报告应该用中文写！                                                     │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─ 内容要求 (5点) ────────────────────────────────────────────────────────┐
# │ 1. 组织结构：# 标题, ## 章节, ### 子章节                                 │
# │ 2. 具体事实：包含研究中的具体数据和洞察                                   │
# │ 3. 引用格式：使用 [Title](URL) 格式                                     │
# │ 4. 全面分析：尽可能详尽，用户期望深度研究                                  │
# │ 5. 来源汇总：末尾包含 "Sources" 章节                                     │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─ 报告结构模板 (4种类型) ─────────────────────────────────────────────────┐
# │                                                                         │
# │ 【类型A：比较型问题】                                                     │
# │ 问题示例："比较 React 和 Vue 的优缺点"                                   │
# │ 结构：1/ 介绍 → 2/ A概述 → 3/ B概述 → 4/ A与B比较 → 5/ 结论              │
# │                                                                         │
# │ 【类型B：列表型问题】                                                     │
# │ 问题示例："列出10个最好的Python库"                                       │
# │ 结构：直接列表，或每个项目一个章节，无需引言和结论                          │
# │                                                                         │
# │ 【类型C：综述型问题】                                                     │
# │ 问题示例："介绍一下机器学习的发展历程"                                    │
# │ 结构：1/ 概述 → 2/ 概念1 → 3/ 概念2 → 4/ 概念3 → 5/ 结论                │
# │                                                                         │
# │ 【类型D：简单问题】                                                       │
# │ 问题示例："什么是REST API？"                                             │
# │ 结构：单一章节直接回答                                                   │
# │                                                                         │
# │ 【灵活性声明】                                                           │
# │ "Section is a VERY fluid and loose concept"                             │
# │ → 不要死板套用模板，根据实际需要调整                                      │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─ 写作规范 (6点) ────────────────────────────────────────────────────────┐
# │ 1. 语言简洁：使用简单清晰的语言                                          │
# │ 2. 格式规范：使用 ## 作为章节标题                                        │
# │ 3. 避免自我指涉：不要说"我认为"、"本报告将..."                            │
# │ 4. 不要元评论：直接写报告，不要描述你在做什么                              │
# │ 5. 内容充实：每章节应足够长，用户期待详细内容                              │
# │ 6. 默认段落：除非必要，否则用段落而非列表                                  │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ┌─ 引用规则 <Citation Rules> ─────────────────────────────────────────────┐
# │                                                                         │
# │ 【格式要求】                                                             │
# │ • 正文中：[1]、[2] 等数字编号                                            │
# │ • 末尾 Sources 章节：                                                   │
# │   [1] Source Title: URL                                                │
# │   [2] Source Title: URL                                                │
# │                                                                         │
# │ 【为什么引用如此重要？】                                                  │
# │ • 增加可信度：用户可以验证信息来源                                        │
# │ • 便于深入：用户可能想进一步了解某个话题                                   │
# │ • 责任追溯：区分代理推断和引用事实                                        │
# │                                                                         │
# │ 【编号规则】                                                             │
# │ • 每个URL只用一个编号（去重）                                             │
# │ • 顺序编号，不能有间隔（1,2,3... 不能是 1,3,5...）                        │
# │ • 每个来源独立成行                                                       │
# └─────────────────────────────────────────────────────────────────────────┘
#
# =============================================================================
# 【第四部分：工具说明】
# =============================================================================
# "You have access to a few tools."
# "## `internet_search`"
#
# 【设计意图】
# • 提醒代理它有工具可用
# • 简要说明工具用途
# • 主代理也可以直接搜索，不一定要通过研究子代理
#
# =============================================================================
# 【总结：主代理提示词的设计艺术】
# =============================================================================
#
# 【优点分析】
# 1. 【层次分明】使用 XML 标签 (<report_instructions>) 组织结构
# 2. 【优先级清晰】CRITICAL、IMPORTANT 等标记突出重点
# 3. 【示例丰富】提供多种报告结构模板
# 4. 【约束明确】语言、格式、引用都有具体要求
# 5. 【灵活性】允许代理自主判断（迭代次数、报告结构）
#
# 【提示词工程技巧】
# • 使用 XML 标签分块：<report_instructions>、<Citation Rules>
# • 关键信息用大写：CRITICAL、IMPORTANT、REMEMBER
# • 提供反例："not the language/country that the question is ABOUT"
# • 解释原因：告诉代理"为什么"而不只是"做什么"
#


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
