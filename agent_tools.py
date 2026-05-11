# agent_tools.py
from datetime import datetime
from langchain_core.tools import tool
from code_executor import execute_python_code
from search_tool import search_web

# ==========================
# 4.16 周四：定义工具
# ==========================
@tool
def get_current_time() -> str:
    """
    获取当前日期和时间。
    当用户询问时间、日期、星期几时，直接调用此工具返回结果。
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool
def calculator(expression: str) -> str:
    """
    计算一个数学表达式。例如: "2 + 2", "100 / 3", "15 * 4"。
    当用户提出数学计算问题时使用。
    """
    try:
        result = eval(expression, {"__builtins__": None}, {"abs": abs, "round": round})
        return str(result)
    except Exception as e:
        return f"计算出错: {e}"

tools = [get_current_time, calculator, execute_python_code, search_web]