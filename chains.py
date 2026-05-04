# chains.py
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from models import CodeReviewResult

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

review_prompt = PromptTemplate(
    input_variables=["code"],
    template="""
你是专业的 Unity C# 代码审查助手。
请审查以下代码，并严格按照 JSON 格式输出审查结果。

待审查代码：
{code}

{format_instructions}

只输出 JSON，不要添加任何额外说明或 Markdown 代码块标记。
""",
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

def get_review_chain(llm):
    """返回结构化审查链"""
    return review_prompt | llm | parser