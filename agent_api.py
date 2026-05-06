# agent_api.py
from email import message
import re
import json
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from langchain_core import messages
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.exceptions import OutputParserException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage
# 导入基础提示词
from prompts import REVIEW_SYSTEM_PROMPT
from chains import review_chat_prompt


from models import (
    AgentRequest, AgentReviewRequest, AgentReviewResponse,
    CodeReviewResult, UnifiedResponse,AgentMemoryRequest
)
from chains import parser

logger = logging.getLogger("code_review_agent")

# ==========================
# 4.17 周五：意图分类 + 思考链提取
# ==========================
CODE_REVIEW_KEYWORDS = [
    "代码", "审查", "review", "优化", "性能", "规范", "c#", "unity",
    "mono", "update", "fixedupdate", "gameobject", "transform",
    "component", "单例", "继承", "public", "private", "class",
    "void", "int", "float", "string", "bool"
]

def is_code_review_intent(user_input: str) -> bool:
    input_lower = user_input.lower()
    return any(keyword in input_lower for keyword in CODE_REVIEW_KEYWORDS)

def extract_thinking_chain(messages: List[Any]) -> tuple[List[Dict], List[str], str]:
    thinking_chain = []
    tool_calls_made = []
    reasoning_parts = []
    for msg in messages:
        msg_type = type(msg).__name__
        if msg_type in ["SystemMessage", "HumanMessage"]:
            content = msg.content
            thinking_chain.append({
                "type": msg_type,
                "content": content[:200] + "..." if len(content) > 200 else content
            })
        elif msg_type == "AIMessage":
            entry = {"type": "AIMessage", "content": msg.content}
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                entry["tool_calls"] = [
                    {"name": tc.get("name"), "args": tc.get("args")}
                    for tc in msg.tool_calls
                ]
                tool_names = [tc.get("name") for tc in msg.tool_calls]
                tool_calls_made.extend(tool_names)
                reasoning_parts.append(f"调用工具: {', '.join(tool_names)}")
            else:
                if msg.content:
                    reasoning_parts.append(msg.content[:100])
            thinking_chain.append(entry)
        elif msg_type == "ToolMessage":
            thinking_chain.append({
                "type": "ToolMessage",
                "tool_name": getattr(msg, "name", "unknown"),
                "result": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            })
    final_reasoning = " → ".join(reasoning_parts) if reasoning_parts else "直接回答，未调用工具"
    return thinking_chain, tool_calls_made, final_reasoning

# ==========================
# 4.18 周六：容错清洗 + 重试
# ==========================
def clean_llm_output(raw_output: str) -> str:
    if not raw_output:
        return ""
    cleaned = raw_output.strip()
    json_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    match = re.search(json_pattern, cleaned)
    if match:
        cleaned = match.group(1).strip()
        logger.info("从 Markdown 代码块中提取了 JSON")
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
        cleaned = cleaned[first_brace:last_brace + 1]
        logger.info("提取了 { } 之间的 JSON 内容")
    common_prefixes = [
        "以下是审查结果：", "审查结果：", "输出：", "Result:", "Output:",
        "Here is the review result:", "The review result is:"
    ]
    for prefix in common_prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            logger.info(f"移除了前缀: {prefix}")
    if cleaned.count("{") > cleaned.count("}"):
        missing = cleaned.count("{") - cleaned.count("}")
        cleaned = cleaned + "}" * missing
        logger.warning(f"自动补全了 {missing} 个缺失的闭合括号")
    return cleaned.strip()

async def safe_parse_with_retry(raw_output: str, parser_obj, max_retries: int = 2) -> Any:
    last_error = None
    current_output = raw_output
    for attempt in range(max_retries + 1):
        try:
            if attempt == 0:
                logger.info("尝试直接解析 LLM 原始输出...")
                return parser_obj.parse(current_output)
            logger.info(f"第 {attempt} 次重试：清洗输出...")
            cleaned = clean_llm_output(current_output)
            if cleaned != current_output:
                logger.info(f"清洗后长度: {len(current_output)} -> {len(cleaned)}")
            return parser_obj.parse(cleaned)
        except OutputParserException as e:
            last_error = e
            logger.warning(f"解析失败 (尝试 {attempt + 1}/{max_retries + 1}): {str(e)[:200]}")
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(f"JSON 解析失败 (尝试 {attempt + 1}/{max_retries + 1}): {str(e)}")
        except Exception as e:
            last_error = e
            logger.error(f"未知解析错误: {str(e)}")
            break
    logger.error(f"所有解析尝试均失败。原始输出前200字符: {raw_output[:200]}")
    raise HTTPException(
        status_code=422,
        detail={
            "error": "LLM 输出格式解析失败，已尝试所有修复策略",
            "last_error": str(last_error) if last_error else "未知错误",
            "hint": "请检查 LLM 输出是否符合预期格式"
        }
    )

# =====================================================
# 4.20 周一：Memory 支持
# =====================================================
session_store:Dict[str, list] = {}

def get_session_history(session_id:str)->List:
    if session_id not in session_store:
        session_store[session_id]=[]
    return session_store[session_id]

def add_message_to_session(session_id:str,message):
    session_store[session_id].append(message)


# ==========================
# 注册 Agent 相关路由
# ==========================
def register_agent_routes(app, llm, agent_graph, review_chain, review_chat_prompt, parser):
    """将 Agent 相关接口注册到 FastAPI app 上"""

    @app.post("/agent")
    async def run_agent(request: AgentRequest):
        system_prompt = SystemMessage(content=REVIEW_SYSTEM_PROMPT)
        result = await agent_graph.ainvoke({
            "messages": [system_prompt, HumanMessage(content=request.input)]
        })
        final_message = result["messages"][-1].content
        return {"output": final_message}  # 保持原样，也可用 UnifiedResponse 包裹

    @app.post("/agent/structured")
    async def run_structured_agent(request: AgentReviewRequest):
        if not is_code_review_intent(request.input):
            return AgentReviewResponse(
                success=True,
                is_code_related=False,
                review_result=None,
                reasoning=f"用户输入与代码审查无关，已拦截",
                tool_calls_made=[],
                thinking_chain=[{"type": "IntentFilter", "result": "rejected"}]
            ).model_dump()
        system_prompt = SystemMessage(content=REVIEW_SYSTEM_PROMPT)
        result = await agent_graph.ainvoke({
            "messages": [system_prompt, HumanMessage(content=request.input)]
        })
        messages = result["messages"]
        thinking_chain, tool_calls_made, reasoning = extract_thinking_chain(messages)
        review_result = None
        if is_code_review_intent(request.input):
            try:
                review_result = await review_chain.ainvoke({"code": request.input})
            except Exception as e:
                reasoning += f" | 结构化解析失败: {str(e)}"
        return AgentReviewResponse(
            success=True,
            is_code_related=True,
            review_result=review_result,
            reasoning=reasoning,
            tool_calls_made=tool_calls_made,
            thinking_chain=thinking_chain
        ).model_dump()

    @app.post("/agent/structured/safe")
    async def safe_structured_agent(request: AgentReviewRequest):
        logger.info(f"收到 Agent 请求，输入长度: {len(request.input)}")
        if not is_code_review_intent(request.input):
            logger.info(f"意图分类：非代码相关，已拦截")
            return AgentReviewResponse(
                success=True,
                is_code_related=False,
                review_result=None,
                reasoning=f"用户输入与代码审查无关，已拦截",
                tool_calls_made=[],
                thinking_chain=[{"type": "IntentFilter", "result": "rejected"}]
            ).model_dump()
        logger.info("意图分类：代码相关，进入 Agent 流程")
        try:
            system_prompt = SystemMessage(content=REVIEW_SYSTEM_PROMPT)
            logger.info("开始执行 Agent 图...")
            result = await agent_graph.ainvoke({
                "messages": [system_prompt, HumanMessage(content=request.input)]
            })
            logger.info("Agent 执行完成")
            messages = result["messages"]
            thinking_chain, tool_calls_made, reasoning = extract_thinking_chain(messages)
            logger.info(f"工具调用记录: {tool_calls_made}")
            review_result = None
            try:
                logger.info("开始调用结构化审查链...")
                raw_review = await (review_chat_prompt | llm).ainvoke({"code": request.input})
                raw_text = raw_review.content if hasattr(raw_review, "content") else str(raw_review)
                review_result = await safe_parse_with_retry(
                    raw_output=raw_text,
                    parser_obj=parser,
                    max_retries=2
                )
                logger.info(f"结构化审查完成，has_problem={review_result.has_problem}")
            except HTTPException as parse_error:
                logger.warning(f"结构化解析失败，将返回空审查结果: {parse_error.detail}")
                reasoning += f" | 结构化解析失败"
            except Exception as e:
                logger.error(f"审查链执行异常: {str(e)}")
                reasoning += f" | 审查链异常"
            return AgentReviewResponse(
                success=True,
                is_code_related=True,
                review_result=review_result,
                reasoning=reasoning,
                tool_calls_made=tool_calls_made,
                thinking_chain=thinking_chain
            ).model_dump()
        except Exception as e:
            logger.exception(f"Agent 接口未知错误: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={"error": "Agent 服务内部错误", "message": str(e)}
            )
    
    @app.post("/agent/memory", 
          summary="带记忆的代码审查 Agent",
          description="""
          支持多轮对话的代码审查接口。
          
          **使用方式**：
          1. 第一轮：传入代码片段（如 `public int age;`），指定一个 `session_id`
          2. 后续轮次：用同一个 `session_id`，可以引用之前的代码（如 "刚才那个字段有什么问题？"）
          
          **注意事项**：
          - 第一轮必须包含代码关键词，否则会被意图分类拦截
          - 同一 `session_id` 下的对话历史会持续累积
          """)
    async def agent_with_memory(request: AgentMemoryRequest):
        """带对话记忆的 Agent 接口"""
        history = get_session_history(request.session_id)
        
        # 只有在「全新会话」且「不包含代码关键词」时才拦截
        if not history and not is_code_review_intent(request.input):
            return UnifiedResponse(
                success=True, code=200, message="非代码请求已拦截",
                data={"output": "请提供与 Unity C# 代码审查相关的问题。"}
            ).model_dump()

        # 构建消息列表
        messages = [SystemMessage(content=REVIEW_SYSTEM_PROMPT)]
        messages.extend(history)
        messages.append(HumanMessage(content=request.input))

        # 执行 Agent
        result = await agent_graph.ainvoke({"messages": messages})

        # 保存本轮对话
        add_message_to_session(request.session_id, HumanMessage(content=request.input))
        add_message_to_session(request.session_id, result["messages"][-1])

        return UnifiedResponse(
            success=True, code=200, message="ok",
            data={"output": result["messages"][-1].content}
        ).model_dump()
    
    # =====================================================
    # 4.22 周三：对话历史管理接口（上方/agent/memory的promt进行修改）
    # =====================================================
    
    @app.get("/agent/memory/history")
    async def get_memory_history(session_id: str = Query(..., description="会话ID")):
        """查看指定会话的对话历史"""
        history = get_session_history(session_id)
        if not history:
            return UnifiedResponse(
                success=True, code=200, message="该会话暂无历史记录",
                data={"session_id": session_id, "history": [], "rounds": 0}
            ).model_dump()
        
        # 将历史消息转为可读格式
        history_list = []
        for msg in history:
            msg_type = type(msg).__name__
            history_list.append({
                "type": msg_type,        # ← 修正：用定义过的变量名
                "content": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            })
        
        return UnifiedResponse(
            success=True, code=200, message="ok",
            data={
                "session_id": session_id,
                "rounds": len(history_list) // 2,   # ← 修正：一问一答为一轮
                "history": history_list             # ← 修正：正确的变量名
            }
        ).model_dump()

    @app.delete("/agent/memory/history")
    async def clear_memory_history(session_id: str = Query(..., description="会话ID")):
        """清除指定会话的对话历史"""
        if session_id in session_store:
            del session_store[session_id]
            return UnifiedResponse(
                success=True, code=200, message=f"会话 {session_id} 的历史记录已清除",
                data=None
            ).model_dump()
        else:
            return UnifiedResponse(
                success=False, code=404, message=f"会话 {session_id} 不存在",
                data=None
            ).model_dump()

    # =====================================================
    # 4.23 周四：支持流式输出 Agent 思考过程
    # =====================================================

    @app.post("/agent/memory/stream")
    async def agent_with_memory_stream(request: AgentMemoryRequest):
        """带对话记忆的流式 Agent 接口"""
        history = get_session_history(request.session_id)
        messages = [SystemMessage(content=REVIEW_SYSTEM_PROMPT)]
        messages.extend(history)
        messages.append(HumanMessage(content=request.input))

        async def stream_events():
            # 拦截逻辑移到生成器内部，此处可以用 return（因为生成器内 return 表示结束生成）
            if not history and not is_code_review_intent(request.input):
                yield f"data: {json.dumps({'type': 'error', 'content': '请提供与 Unity C# 代码审查相关的问题。'})}\n\n"
                return  # 生成器结束
            
            full_response = ""
            try:
                async for event in agent_graph.astream_events({"messages": messages}, version="v2"):
                    kind = event.get("event")
                    
                    if kind == "on_chat_model_stream":
                        chunk = event["data"]["chunk"]
                        if hasattr(chunk, "content") and chunk.content:
                            full_response += chunk.content
                            yield f"data: {json.dumps({'type': 'text', 'content': chunk.content})}\n\n"
                    
                    elif kind == "on_tool_start":
                        tool_name = event["name"]
                        yield f"data: {json.dumps({'type': 'tool_start', 'content': f'正在调用工具: {tool_name}...'})}\n\n"
                    
                    elif kind == "on_tool_end":
                        tool_name = event["name"]
                        yield f"data: {json.dumps({'type': 'tool_end', 'content': f'工具 {tool_name} 调用完成'})}\n\n"
            
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': f'执行错误: {str(e)}'})}\n\n"
            finally:
                yield f"data: {json.dumps({'type': 'done', 'content': full_response})}\n\n"
                add_message_to_session(request.session_id, HumanMessage(content=request.input))
                if full_response:
                    add_message_to_session(request.session_id, AIMessage(content=full_response))

        return StreamingResponse(stream_events(), media_type="text/event-stream")
