# chains.py
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from models import CodeReviewResult
from prompts import FEW_SHOT_EXAMPLES

# ==========================
# 4.14 周二：LLMChain 提示词
# ==========================
prompt_template = PromptTemplate(
    input_variables=["user_input"],
    template="""
你是专业的 Unity C# 代码审查助手。
用户问题：{user_input}
请给出简洁、专业的回答。
"""
)

# ==========================
# 4.15 周三：结构化输出
# ==========================
parser = PydanticOutputParser(pydantic_object=CodeReviewResult)

# =====================================================
# 5.6 修改：从 PromptTemplate 改为 ChatPromptTemplate
# =====================================================
review_chat_prompt = ChatPromptTemplate.from_messages([
    ("system", FEW_SHOT_EXAMPLES),
    ("user", "{code}")
])

# 预填入 format_instructions，使其在系统消息中生效
review_chat_prompt = review_chat_prompt.partial(
    format_instructions=parser.get_format_instructions()
)

def get_review_chain(llm):
    """返回结构化审查链"""
    return review_chat_prompt | llm | parser