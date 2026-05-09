# main.py
import asyncio
import os
import logging
from datetime import datetime

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from starlette.responses import StreamingResponse
from langchain_openai import ChatOpenAI

from config import config
from models import ChatRequest, ChainRequest, CodeReviewRequest, SafeReviewRequest, UnifiedResponse
from chains import prompt_template, get_review_chain, review_chat_prompt, parser
from agent_graph import get_agent_graph
from agent_api import register_agent_routes
from prompts import REVIEW_SYSTEM_PROMPT

from models import CodeGenResult,CodeGenRequest
from chains import get_code_gen_chain

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("code_review_agent")

# FastAPI 实例
app = FastAPI(title="DeepSeek Chat API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI 客户端（SSE 用）
client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.LLM_BASE_URL
)

async def generate_stream(prompt: str, history: list[dict] | None = None):
    try:
        messages = []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        stream = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            stream=True
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                yield f"data: {content}\n\n"
                await asyncio.sleep(0.02)
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: [ERROR: {str(e)}]\n\n"

@app.get('/chat-stream')
async def chat_stream(prompt: str = Query(..., min_length=1)):
    return StreamingResponse(generate_stream(prompt), media_type="text/event-stream")

@app.post('/chat-stream-history')
async def chat_stream_history(request: ChatRequest):
    return StreamingResponse(
        generate_stream(request.message, request.history),
        media_type="text/event-stream"
    )

# 初始化 LLM
llm = ChatOpenAI(
    model=config.LLM_MODEL,
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.LLM_BASE_URL,
    temperature=config.LLM_TEMPERATURE
)

# 获取各组件
review_chain = get_review_chain(llm)
agent_graph = get_agent_graph(llm)

# 基础接口
@app.post("/chain")
async def run_chain(request: ChainRequest):
    chain = prompt_template | llm
    result = await chain.ainvoke({"user_input": request.user_input})
    return {"input": request.user_input, "output": result.content}

@app.post("/review")
async def review_code(request: CodeReviewRequest):
    result = await review_chain.ainvoke({"code": request.code})
    return result

@app.post("/review/safe")
async def safe_review_code(request: SafeReviewRequest):
    logger.info(f"收到审查请求，代码长度: {len(request.code)}")
    try:
        raw_result = await (review_chat_prompt | llm).ainvoke({"code": request.code})
        raw_text = raw_result.content if hasattr(raw_result, "content") else str(raw_result)
        logger.info(f"LLM 返回原始输出，长度: {len(raw_text)}")
        # 延迟导入 safe_parse_with_retry 避免循环
        from agent_api import safe_parse_with_retry
        parsed_result = await safe_parse_with_retry(raw_text, parser, max_retries=2)
        logger.info(f"审查完成，has_problem={parsed_result.has_problem}")
        return parsed_result
    except Exception as e:
        logger.exception(f"审查接口未知错误: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": "服务内部错误", "message": str(e)})

# 注册 Agent 相关路由
register_agent_routes(app, llm, agent_graph, review_chain, review_chat_prompt, parser)

# 全局异常处理器（与源文件一致）
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from langchain_core.exceptions import OutputParserException

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "status_code": exc.status_code
        }
    )

@app.exception_handler(OutputParserException)
async def output_parser_exception_handler(request, exc: OutputParserException):
    logger.error(f"OutputParserException: {str(exc)[:200]}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "LLM 输出格式解析失败",
            "detail": str(exc)[:500],
            "hint": "请检查提示词模板或调整输出格式约束"
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    logger.exception(f"未处理的异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "服务内部错误",
            "message": str(exc) if logger.level == logging.DEBUG else "请联系管理员"
        }
    )

# =====================================================
# 5.8 周四：代码生成 Chain 集成
# =====================================================

# 构建代码生成链
# 功能说明：将用户用自然语言描述的编程需求，
# 交给 LLM 生成对应语言的代码，并以结构化 JSON 返回。
code_gen_chain = get_code_gen_chain(llm)

@app.post("/code_gen")
async def generate_code(request:CodeGenRequest):
    """根据需求生成代码"""
    # 将用户输入注入链中，触发 LLM 生成代码
    result = await code_gen_chain.ainvoke({"user_input": request.user_input})

    # 将结构化结果包装在统一响应中返回
    return UnifiedResponse(
        success=True,
        code=200,
        message="代码生成成功",
        data=result.model_dump()
    ).model_dump()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)


# {
#   "user_input": "写一个 Unity 脚本，让摄像机跟随玩家角色，平滑移动"
# }