# models.py
from typing import Optional, Any, List, Dict
import langchain_openai
from pydantic import BaseModel, Field

# ==========================
# 通用请求响应模型
# ==========================
class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入的消息", min_length=1)
    history: list[dict] | None = Field(default=None, description="历史对话列表，格式：[{role, content}]")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI 的回答")
    status: str = Field(default="success", description="处理状态")

# ==========================
# 4.14 周二
# ==========================
class ChainRequest(BaseModel):
    user_input: str

# ==========================
# 4.15 周三
# ==========================
class CodeReviewResult(BaseModel):
    """Unity C# 代码审查结果"""
    has_problem: bool = Field(description="代码是否存在问题")
    issues: list[str] = Field(description="发现的问题列表，如命名不规范、性能隐患等")
    suggestions: list[str] = Field(description="具体的优化建议列表")
    improved_code: str = Field(description="优化后的完整代码片段")

class CodeReviewRequest(BaseModel):
    code: str = Field(..., description="待审查的 Unity C# 代码")

# ==========================
# 4.16 周四
# ==========================
class AgentRequest(BaseModel):
    input: str

# ==========================
# 4.17 周五
# ==========================
class AgentReviewResponse(BaseModel):
    """Agent 审查的完整结构化响应"""
    success: bool = Field(description="请求是否成功处理")
    is_code_related: bool = Field(description="用户输入是否与代码审查相关")
    review_result: Optional[CodeReviewResult] = Field(
        default=None,
        description="审查结果（仅当 is_code_related=True 时有值）"
    )
    reasoning: str = Field(description="Agent 的推理过程简述")
    tool_calls_made: List[str] = Field(default=[], description="实际调用的工具列表")
    thinking_chain: List[Dict[str, Any]] = Field(default=[], description="完整的思考链记录")

class AgentReviewRequest(BaseModel):
    input: str = Field(..., description="用户输入的内容")

# ==========================
# 4.18 周六
# ==========================
class SafeReviewRequest(BaseModel):
    code: str = Field(..., description="待审查的 Unity C# 代码")

# ==========================
# 4.20 周日：统一响应模型（新增）
# ==========================
class UnifiedResponse(BaseModel):
    success: bool = Field(..., description="请求是否成功")
    code: int = Field(default=200, description="业务状态码")
    message: str = Field(default="ok", description="提示信息")
    data: Optional[Any] = Field(default=None, description="响应数据")

# ==========================
# 4.20 周一：Memory 支持
# ==========================
class AgentMemoryRequest(BaseModel):
    input:str=Field(...,description="用户输入")
    session_id:str=Field(default="default",description="绘画id")

# =====================================================
# 5.8 周四：代码生成器请求模型
# =====================================================
class CodeGenRequest(BaseModel):
    """代码生成请求"""
    user_input: str = Field(..., description="用户的需求描述", min_length=1)

# =====================================================
# 5.8 周四：代码生成器输出模型
# =====================================================
class CodeGenResult(BaseModel):
    """代码生成结果"""
    requirement: str = Field(description="用户的需求描述")
    language: str = Field(description="生成代码的语言，如 python、csharp、javascript 等")
    code: str = Field(description="生成的代码片段，不包含 Markdown 代码块标记")
    explanation: str = Field(description="对生成代码的简要解释，包括关键实现思路和注意事项")