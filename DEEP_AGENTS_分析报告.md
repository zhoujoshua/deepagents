# Deep Agents 核心代码与架构分析

## 一、项目概述

Deep Agents 是一个受 Claude Code 启发的通用 AI Agent 框架，基于 LangGraph 和 LangChain 构建。它提供了规划能力、文件系统操作和子代理（subagent）管理功能。

**核心特性：**
- 🧠 规划与任务管理（TodoList）
- 📁 文件系统操作（读写编辑搜索）
- 🤖 子代理系统（任务隔离与并行）
- 💾 多后端存储（State/Store/Filesystem）
- 🔄 消息摘要与提示词缓存

---

## 二、核心架构

### 2.1 主要组件层次

```
create_deep_agent() - 工厂函数
├── 模型层: Claude Sonnet 4.5 (默认)
├── 中间件栈 (Middleware Stack)
│   ├── TodoListMiddleware          # 任务规划
│   ├── FilesystemMiddleware        # 文件操作
│   ├── SubAgentMiddleware          # 子代理管理
│   ├── SummarizationMiddleware     # 消息摘要
│   ├── AnthropicPromptCachingMiddleware  # 提示词缓存
│   └── PatchToolCallsMiddleware    # 工具调用修复
├── 后端存储 (Backend)
│   ├── StateBackend                # 状态存储（临时）
│   ├── StoreBackend                # 持久化存储
│   ├── FilesystemBackend           # 文件系统
│   └── CompositeBackend            # 组合路由
└── 工具集 (Tools)
    ├── write_todos                 # 规划工具
    ├── ls, read_file, write_file   # 文件工具
    ├── edit_file, glob, grep       # 编辑搜索
    ├── task                        # 子代理调用
    ├── shell                       # Shell执行
    ├── web_search                  # 网络搜索
    └── http_request                # HTTP请求
```

### 2.2 核心文件说明

| 文件路径 | 功能 | 关键代码 |
|---------|------|---------|
| `libs/deepagents/graph.py` | 主工厂函数 | `create_deep_agent()` (143行) |
| `libs/deepagents/middleware/filesystem.py` | 文件系统中间件 | 6个文件工具 + 大结果驱逐机制 |
| `libs/deepagents/middleware/subagents.py` | 子代理中间件 | `task` 工具 + 子代理编排 |
| `libs/deepagents/backends/state.py` | 状态后端 | LangGraph状态管理 |
| `libs/deepagents-cli/deepagents_cli/agent.py` | CLI代理配置 | 人机交互中间件配置 |

---

## 三、提示词系统分析

### 3.1 系统提示词结构

```
最终系统提示词 = 自定义提示词 + BASE_AGENT_PROMPT + 中间件提示词
```

#### 基础提示词 (BASE_AGENT_PROMPT)
```python
# 位置: libs/deepagents/graph.py:25
BASE_AGENT_PROMPT = "In order to complete the objective that the user asks of you, you have access to a number of standard tools."
```

#### 文件系统提示词 (FILESYSTEM_SYSTEM_PROMPT)
```markdown
## Filesystem Tools: ls, read_file, write_file, edit_file, glob, grep

你可以访问文件系统，所有路径必须以 / 开头：
- ls: 列出目录文件（需要绝对路径）
- read_file: 读取文件（支持分页：offset/limit）
- write_file: 写入新文件
- edit_file: 编辑现有文件（精确字符串替换）
- glob: 查找文件（支持通配符 *, **, ?）
- grep: 搜索文件内容
```

#### 子代理提示词 (TASK_SYSTEM_PROMPT)
```markdown
## task (子代理生成器)

你可以使用 task 工具启动短暂的子代理来处理隔离任务。

**何时使用：**
- 任务复杂且多步骤，可完全独立委托
- 任务独立，可并行运行
- 任务需要集中推理或大量 token/上下文
- 沙箱化提高可靠性
- 只关心输出，不关心中间步骤

**子代理生命周期：**
1. Spawn → 提供清晰角色、指令和预期输出
2. Run → 子代理自主完成任务
3. Return → 返回单一结构化结果
4. Reconcile → 整合结果到主线程
```

### 3.2 CLI 默认提示词

**位置：** `libs/deepagents-cli/deepagents_cli/default_agent_prompt.md`

**核心指令：**
1. **记忆协议：** 会话开始检查 `/memories/` 目录
2. **风格要求：** 简洁直接，少于4行（除非用户要求详细）
3. **文件读取最佳实践：** 大文件使用分页（limit=100）
4. **子代理协作：** 大输入/输出通过文件传递
5. **任务管理：** 3+步骤使用 write_todos

---

## 四、运行流程详解

### 4.1 Agent 创建流程

```python
# 1. 创建 Deep Agent
agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",  # 默认模型
    tools=[internet_search],              # 自定义工具
    system_prompt=research_instructions,  # 系统提示词
    subagents=[research_sub_agent],       # 子代理定义
    backend=backend,                      # 存储后端
    middleware=[custom_middleware],       # 额外中间件
)
```

**内部步骤：**

```
create_deep_agent()
  ↓
1. 初始化模型 (get_default_model() 或自定义)
  ↓
2. 构建中间件栈
   - TodoListMiddleware()
   - FilesystemMiddleware(backend)
   - SubAgentMiddleware(
       default_middleware=[
           TodoListMiddleware(),
           FilesystemMiddleware(backend),
           SummarizationMiddleware(max_tokens=170000),
           AnthropicPromptCachingMiddleware(),
           PatchToolCallsMiddleware(),
       ]
     )
   - SummarizationMiddleware()
   - AnthropicPromptCachingMiddleware()
   - PatchToolCallsMiddleware()
   - 自定义 middleware
  ↓
3. 组装系统提示词
   system_prompt + "\n\n" + BASE_AGENT_PROMPT
  ↓
4. 调用 create_agent() (LangChain)
  ↓
5. 设置递归限制: recursion_limit=1000
  ↓
返回: CompiledStateGraph
```

### 4.2 工具调用流程

#### 示例：读取文件

```
用户: "读取 /src/main.py"
  ↓
Agent 生成工具调用:
  {
    "name": "read_file",
    "args": {
      "file_path": "/src/main.py",
      "offset": 0,
      "limit": 500
    }
  }
  ↓
FilesystemMiddleware.wrap_tool_call()
  ↓
_read_file_tool_generator() 执行
  ↓
Backend.read(file_path, offset, limit)
  ↓
返回格式化内容（带行号）:
  "     1→import os
       2→from typing import Any
       3→..."
  ↓
检查结果大小（>20000 tokens?）
  如果太大 → 保存到 /large_tool_results/{tool_call_id}
  ↓
返回 ToolMessage 给 Agent
```

#### 示例：启动子代理

```
用户: "研究 LeBron James 和 Michael Jordan 的成就并比较"
  ↓
Agent 生成并行工具调用:
  [
    {
      "name": "task",
      "args": {
        "subagent_type": "research-agent",
        "description": "研究 LeBron James 的职业成就..."
      }
    },
    {
      "name": "task",
      "args": {
        "subagent_type": "research-agent",
        "description": "研究 Michael Jordan 的职业成就..."
      }
    }
  ]
  ↓
SubAgentMiddleware 处理每个任务
  ↓
为每个子代理创建隔离状态:
  subagent_state = {
    "messages": [HumanMessage(description)],
    "files": {...},  # 继承主代理状态
    # 排除: "todos", "messages" (主代理的)
  }
  ↓
并行执行子代理:
  result1 = subagent.invoke(subagent_state)
  result2 = subagent.invoke(subagent_state)
  ↓
提取最后消息返回给主代理:
  Command(update={
    "messages": [ToolMessage(result["messages"][-1].text)]
  })
  ↓
主代理综合两个结果
  ↓
返回最终比较报告给用户
```

### 4.3 消息流与状态更新

```
用户输入
  ↓
[HumanMessage(content="用户问题")]
  ↓
┌─────────────────────────────────────────┐
│ 中间件层 (按顺序执行)                    │
│                                          │
│ wrap_model_call():                       │
│  - 注入系统提示词                        │
│  - 添加工具定义                          │
│  - 应用提示词缓存                        │
└─────────────────────────────────────────┘
  ↓
Claude 模型推理
  ↓
AIMessage(tool_calls=[...])
  ↓
┌─────────────────────────────────────────┐
│ 工具执行层                               │
│                                          │
│ wrap_tool_call():                        │
│  - 验证参数                              │
│  - 执行工具逻辑                          │
│  - 检查结果大小（驱逐大结果）            │
│  - 更新状态（文件、记忆等）              │
└─────────────────────────────────────────┘
  ↓
[ToolMessage(content="工具结果")]
  ↓
状态更新 (通过 Command)
  state["files"] = {...}  # 更新文件
  state["messages"].append(...)  # 添加消息
  ↓
下一轮推理循环...
  ↓
最终 AIMessage (无工具调用)
  ↓
返回给用户
```

---

## 五、工具调用方法详解

### 5.1 文件系统工具

#### 1. **ls** - 列出目录

```python
@tool(description=LIST_FILES_TOOL_DESCRIPTION)
def ls(runtime: ToolRuntime, path: str) -> list[str]:
    validated_path = _validate_path(path)  # 安全检查
    infos = backend.ls_info(validated_path)
    return [fi.get("path", "") for fi in infos]
```

**调用示例：**
```python
# Agent 内部
ls(path="/src/")
# 返回: ["/src/main.py", "/src/utils.py", "/src/config/"]
```

#### 2. **read_file** - 读取文件

```python
@tool(description=READ_FILE_TOOL_DESCRIPTION)
def read_file(
    file_path: str,
    runtime: ToolRuntime,
    offset: int = 0,      # 默认从第0行开始
    limit: int = 500,     # 默认读500行
) -> str:
    file_path = _validate_path(file_path)
    return backend.read(file_path, offset=offset, limit=limit)
```

**返回格式：**
```
     1→import os
     2→from typing import Any
     3→
     4→def main():
     5→    print("Hello")
```

**分页读取示例：**
```python
# 第一次：扫描文件结构（前100行）
read_file("/large_file.py", limit=100)

# 第二次：读取特定区域（第100-200行）
read_file("/large_file.py", offset=100, limit=100)
```

#### 3. **write_file** - 写入文件

```python
@tool(description=WRITE_FILE_TOOL_DESCRIPTION)
def write_file(
    file_path: str,
    content: str,
    runtime: ToolRuntime,
) -> Command | str:
    res: WriteResult = backend.write(file_path, content)
    if res.error:
        return res.error
    # 返回 Command 更新状态
    return Command(update={
        "files": res.files_update,
        "messages": [ToolMessage(content=f"Updated file {res.path}")]
    })
```

#### 4. **edit_file** - 编辑文件

```python
@tool(description=EDIT_FILE_TOOL_DESCRIPTION)
def edit_file(
    file_path: str,
    old_string: str,      # 要替换的字符串（必须唯一）
    new_string: str,      # 新字符串
    runtime: ToolRuntime,
    replace_all: bool = False,  # 是否替换所有匹配
) -> Command | str:
    res: EditResult = backend.edit(
        file_path, old_string, new_string, replace_all=replace_all
    )
    return Command(update={
        "files": res.files_update,
        "messages": [ToolMessage(
            content=f"Successfully replaced {res.occurrences} instance(s)"
        )]
    })
```

**重要规则：**
- 必须先 read_file 再 edit_file
- old_string 必须在文件中唯一（除非 replace_all=True）
- 保持精确缩进（从行号后的 TAB 开始）

#### 5. **glob** - 模式匹配查找

```python
@tool(description=GLOB_TOOL_DESCRIPTION)
def glob(
    pattern: str,     # 如: "**/*.py", "*.txt"
    runtime: ToolRuntime,
    path: str = "/",  # 搜索根目录
) -> list[str]:
    infos = backend.glob_info(pattern, path=path)
    return [fi.get("path", "") for fi in infos]
```

**使用示例：**
```python
glob("**/*.py")          # 所有Python文件
glob("*.txt")            # 根目录的文本文件
glob("/src/**/*.test.js") # src下的测试文件
```

#### 6. **grep** - 内容搜索

```python
@tool(description=GREP_TOOL_DESCRIPTION)
def grep(
    pattern: str,        # 搜索文本（非正则）
    runtime: ToolRuntime,
    path: str | None = None,
    glob: str | None = None,  # 文件过滤
    output_mode: Literal["files_with_matches", "content", "count"] = "files_with_matches",
) -> str:
    raw = backend.grep_raw(pattern, path=path, glob=glob)
    formatted = format_grep_matches(raw, output_mode)
    return truncate_if_too_long(formatted)
```

**输出模式：**
- `files_with_matches`: 只返回包含匹配的文件路径（默认）
- `content`: 显示匹配行及上下文
- `count`: 显示每个文件的匹配数量

### 5.2 子代理工具

#### task - 启动子代理

```python
@StructuredTool.from_function(name="task")
def task(
    description: str,      # 任务描述（给子代理的指令）
    subagent_type: str,    # 子代理类型
    runtime: ToolRuntime,
) -> Command:
    # 1. 验证子代理类型
    if subagent_type not in subagent_graphs:
        raise ValueError(f"Unknown subagent type: {subagent_type}")

    # 2. 准备隔离状态
    subagent_state = {
        k: v for k, v in runtime.state.items()
        if k not in ("messages", "todos")  # 排除主代理上下文
    }
    subagent_state["messages"] = [HumanMessage(content=description)]

    # 3. 执行子代理
    subagent = subagent_graphs[subagent_type]
    result = subagent.invoke(subagent_state)

    # 4. 返回最后消息
    return Command(update={
        "messages": [ToolMessage(result["messages"][-1].text)]
    })
```

**并行调用示例（研究代理）：**
```python
# 主代理内部逻辑
[
    task(
        description="研究主题A的详细信息...",
        subagent_type="research-agent"
    ),
    task(
        description="研究主题B的详细信息...",
        subagent_type="research-agent"
    ),
    task(
        description="研究主题C的详细信息...",
        subagent_type="research-agent"
    )
]
# 三个子代理并行运行，各自独立消耗 token
```

### 5.3 外部工具

#### web_search - 网络搜索

```python
def web_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """使用 Tavily 搜索网络"""
    search_docs = tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
    return search_docs
```

**返回结构：**
```json
{
  "results": [
    {
      "title": "页面标题",
      "url": "https://...",
      "content": "相关摘录...",
      "score": 0.95
    }
  ],
  "query": "原始查询"
}
```

#### http_request - HTTP 请求

```python
def http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] = None,
    data: str | dict = None,
    params: dict[str, str] = None,
    timeout: int = 30,
) -> dict:
    """发送 HTTP 请求到 API"""
    response = requests.request(method, url, ...)
    return {
        "success": response.status_code < 400,
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "content": response.json() or response.text,
    }
```

---

## 六、后端存储系统

### 6.1 后端类型对比

| 后端类型 | 存储位置 | 持久性 | 使用场景 |
|---------|---------|--------|---------|
| **StateBackend** | LangGraph State | 单会话 | 临时文件、工具结果 |
| **StoreBackend** | LangGraph Store | 跨会话 | 长期记忆 `/memories/` |
| **FilesystemBackend** | 真实文件系统 | 永久 | 代码库操作 |
| **CompositeBackend** | 路由组合 | 混合 | 不同路径不同策略 |

### 6.2 CompositeBackend 路由示例

```python
# CLI 配置 (libs/deepagents-cli/deepagents_cli/agent.py:160)
backend = CompositeBackend(
    default=FilesystemBackend(),  # 默认：当前工作目录
    routes={
        "/memories/": long_term_backend  # /memories/ → 持久化存储
    }
)
```

**路由逻辑：**
```
read_file("/src/main.py")        → FilesystemBackend (真实文件)
read_file("/memories/guide.md")  → long_term_backend (持久化)
write_file("/temp.txt")          → FilesystemBackend
write_file("/memories/note.md")  → long_term_backend
```

### 6.3 StateBackend 实现细节

```python
class StateBackend(BackendProtocol):
    def __init__(self, runtime: ToolRuntime):
        self.runtime = runtime

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        # 从状态读取文件
        files = self.runtime.state.get("files", {})
        if file_path not in files:
            return f"Error: File '{file_path}' not found"

        file_data = files[file_path]
        content_lines = file_data.get("content", [])

        # 分页处理
        selected_lines = content_lines[offset:offset + limit]

        # 格式化输出（带行号）
        return format_content_with_line_numbers(
            selected_lines,
            start_line=offset + 1
        )

    def write(self, file_path: str, content: str) -> WriteResult:
        # 创建文件数据
        file_data = create_file_data(content)

        # 返回状态更新（不直接修改）
        return WriteResult(
            path=file_path,
            files_update={file_path: file_data},
            error=None
        )
```

**关键点：**
- StateBackend 不直接修改状态，返回更新字典
- 通过 Command 对象更新 LangGraph 状态
- 自动 checkpoint，支持时间旅行调试

---

## 七、中间件机制

### 7.1 中间件接口

```python
class AgentMiddleware:
    # 包装模型调用（注入提示词、工具）
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        # 修改 request.system_prompt
        # 修改 request.tools
        return handler(request)

    # 包装工具调用（拦截、修改结果）
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        # 执行前验证
        result = handler(request)
        # 执行后处理
        return result
```

### 7.2 FilesystemMiddleware 大结果驱逐

```python
# libs/deepagents/middleware/filesystem.py:592
def _intercept_large_tool_result(
    self,
    tool_result: ToolMessage,
    runtime: ToolRuntime
) -> ToolMessage | Command:
    content = tool_result.content

    # 检查大小（默认 20000 tokens ≈ 80000 字符）
    if len(content) > 4 * self.tool_token_limit_before_evict:
        # 保存到虚拟文件系统
        file_path = f"/large_tool_results/{tool_call_id}"
        backend.write(file_path, content)

        # 返回简化消息
        return ToolMessage(
            content=f"工具结果过大，已保存到 {file_path}\n"
                    f"使用 read_file 分页读取（offset/limit）\n"
                    f"前10行预览：\n{content[:1000]}...",
            tool_call_id=tool_call_id
        )

    return tool_result
```

**优势：**
- 防止上下文溢出
- 自动管理大型输出
- 引导 Agent 使用分页

### 7.3 SummarizationMiddleware 消息摘要

```python
# 配置 (libs/deepagents/graph.py:108)
SummarizationMiddleware(
    model=model,
    max_tokens_before_summary=170000,  # 触发摘要的阈值
    messages_to_keep=6,                # 保留最近6条消息
)
```

**工作原理：**
1. 监控对话历史 token 数
2. 超过 170k tokens → 触发摘要
3. 保留最近 6 条消息
4. 旧消息通过 LLM 压缩成摘要
5. 插入摘要消息到历史

---

## 八、实战示例分析

### 8.1 研究代理示例

**文件：** `examples/research/research_agent.py`

#### 架构设计

```
主代理 (研究协调者)
  ├─ 工具: internet_search
  ├─ 子代理1: research-agent (深度研究)
  │   └─ 工具: internet_search
  └─ 子代理2: critique-agent (报告评审)
      └─ 工具: internet_search
```

#### 工作流程

```python
# 1. 用户提问
"研究人工智能的最新进展"

# 2. 主代理规划
write_file("/question.txt", "研究人工智能的最新进展")
write_todos([
    "分解研究子主题",
    "并行调用研究代理",
    "撰写初稿到 /final_report.md",
    "调用评审代理",
    "根据反馈修订"
])

# 3. 并行研究（子代理隔离）
task(description="研究大语言模型进展", subagent_type="research-agent")
task(description="研究计算机视觉进展", subagent_type="research-agent")
task(description="研究强化学习进展", subagent_type="research-agent")
# 每个子代理独立执行 web_search，各自消耗 token

# 4. 主代理综合
write_file("/final_report.md", """
# 人工智能最新进展

## 大语言模型
[子代理1的研究结果]

## 计算机视觉
[子代理2的研究结果]

## 强化学习
[子代理3的研究结果]
""")

# 5. 评审循环
task(
    description="评审 /final_report.md，重点关注深度和全面性",
    subagent_type="critique-agent"
)
# 收到反馈 → 修订报告 → 再次评审（可选）

# 6. 完成
read_file("/final_report.md")  # 返回给用户
```

#### 关键技巧

1. **文件传递大数据**
   ```python
   # 子代理提示词
   "你可以在 final_report.md 找到报告"
   "你可以在 question.txt 找到原始问题"
   ```

2. **并行化研究**
   - 每个子主题独立子代理
   - 避免主代理上下文污染
   - 最终只接收摘要结果

3. **迭代改进**
   ```python
   while not satisfied:
       critique = task(subagent_type="critique-agent")
       edit_file("/final_report.md", ...)
   ```

### 8.2 CLI 代理配置

**文件：** `libs/deepagents-cli/deepagents_cli/agent.py:141`

#### 人机交互中间件

```python
interrupt_on = {
    "shell": InterruptOnConfig({
        "allowed_decisions": ["approve", "reject"],
        "description": lambda tool_call, state, runtime: (
            f"Shell Command: {tool_call['args'].get('command')}\n"
            f"Working Directory: {os.getcwd()}"
        ),
    }),
    "write_file": InterruptOnConfig({...}),
    "edit_file": InterruptOnConfig({...}),
    "web_search": InterruptOnConfig({...}),
    "task": InterruptOnConfig({...}),
}
```

**用户体验：**
```
Agent: 我想执行 shell 命令
───────────────────────────────
Shell Command: rm -rf /data/*
Working Directory: /home/user/project
───────────────────────────────
[approve / reject]?

用户输入: reject

Agent: 理解，我不会删除文件。
      我们可以先用 ls /data/ 查看内容吗？
```

---

## 九、性能优化策略

### 9.1 提示词缓存

```python
# libs/deepagents/graph.py:112
AnthropicPromptCachingMiddleware(
    unsupported_model_behavior="ignore"
)
```

**缓存内容：**
- 系统提示词
- 工具定义
- 对话历史前缀

**效果：**
- 减少重复 token 计费
- 加速推理速度（缓存命中）

### 9.2 消息摘要

```python
# 170k tokens 后自动触发
SummarizationMiddleware(
    max_tokens_before_summary=170000,
    messages_to_keep=6,
)
```

**示例：**
```
原始历史 (200k tokens):
  [消息1...消息100]

摘要后 (80k tokens):
  [摘要: "用户要求实现功能X，经过Y步骤..."]
  [消息95...消息100]  # 保留最近6条
```

### 9.3 子代理隔离

**Token 对比：**

| 方案 | 主代理 Token | 总 Token |
|-----|-------------|----------|
| 单代理研究3个主题 | 150k | 150k |
| 3个子代理并行 | 30k (摘要) | 90k (3×25k + 主代理15k) |

**优势：**
- 子代理只返回摘要（节省主代理 token）
- 并行执行（节省时间）
- 上下文隔离（提高质量）

### 9.4 分页读取

```python
# 坏示例：一次读取大文件
read_file("/large_file.py")  # 10000行 → 占用大量上下文

# 好示例：分页扫描
read_file("/large_file.py", limit=100)  # 快速了解结构
read_file("/large_file.py", offset=500, limit=200)  # 精准读取目标区域
```

---

## 十、最佳实践总结

### 10.1 文件操作

✅ **推荐做法：**
```python
# 1. 先 ls 探索结构
ls("/src/")

# 2. 分页读取
read_file("/src/main.py", limit=100)

# 3. 编辑前必读
read_file("/src/main.py")
edit_file("/src/main.py", old="...", new="...")
```

❌ **避免：**
```python
# 盲目写入（不检查现有代码）
write_file("/src/main.py", "...")

# 不读取直接编辑
edit_file("/src/main.py", ...)  # 会报错
```

### 10.2 子代理使用

✅ **推荐场景：**
- 复杂多步任务（>5步）
- 独立并行任务
- 需要大量上下文的研究
- 预期输出可压缩成摘要

❌ **避免场景：**
- 简单1-2步任务
- 需要查看中间步骤
- 主代理已有所需上下文

### 10.3 提示词设计

✅ **清晰分层：**
```
系统提示词 (角色定义)
  + 工具提示词 (使用说明)
  + 任务提示词 (当前目标)
```

✅ **具体指令：**
```markdown
# 好
"读取 /src/ 下所有 .py 文件，找到定义 User 类的文件"

# 坏
"找一下用户相关代码"
```

### 10.4 记忆管理

✅ **结构化存储：**
```
/memories/
  ├── project-architecture.md  # 项目结构
  ├── api-endpoints.md         # API文档
  └── troubleshooting.md       # 问题记录
```

✅ **会话开始检查：**
```python
# Agent 内部逻辑（default_agent_prompt.md:9）
ls("/memories/")  # 查看已有知识
read_file("/memories/project-architecture.md")  # 加载相关记忆
```

---

## 十一、技术栈总结

| 层级 | 技术 | 版本要求 |
|-----|------|---------|
| **AI 模型** | Claude Sonnet 4.5 | 2025-09-29 |
| **框架** | LangGraph | - |
| **Agent** | LangChain Agents | - |
| **HTTP** | requests | - |
| **搜索** | Tavily API | - |
| **语言** | Python | ≥3.11, <4.0 |
| **代码风格** | Ruff | 行长150 |
| **类型检查** | MyPy | strict模式 |

---

## 十二、关键代码位置速查

| 功能 | 文件路径 | 行号 |
|-----|---------|-----|
| Agent 工厂函数 | `libs/deepagents/graph.py` | 40-143 |
| 文件系统工具生成 | `libs/deepagents/middleware/filesystem.py` | 242-441 |
| 子代理工具生成 | `libs/deepagents/middleware/subagents.py` | 279-372 |
| 默认提示词 | `libs/deepagents-cli/deepagents_cli/default_agent_prompt.md` | 全文 |
| CLI 代理创建 | `libs/deepagents-cli/deepagents_cli/agent.py` | 141-271 |
| StateBackend 实现 | `libs/deepagents/backends/state.py` | 20-150 |
| 研究代理示例 | `examples/research/research_agent.py` | 全文 |
| Web 搜索工具 | `libs/deepagents-cli/deepagents_cli/tools.py` | 92-141 |

---

## 总结

Deep Agents 是一个精心设计的多层架构 AI Agent 框架，核心优势在于：

1. **模块化设计**：中间件栈清晰分离关注点
2. **灵活存储**：多后端支持临时/持久/混合策略
3. **智能优化**：自动摘要、缓存、大结果驱逐
4. **子代理隔离**：并行执行、上下文隔离、token优化
5. **安全可控**：路径验证、人机交互、工具审批

通过研究其核心代码，可以学习到：
- Agent 工具设计的最佳实践
- 复杂任务的分解与编排
- 提示词工程的分层策略
- 存储后端的抽象与路由

这些设计思想可直接应用于构建自定义 AI Agent 系统。
