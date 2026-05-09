# agent_tools.py
from datetime import datetime
from langchain_core.tools import tool
from code_executor import execute_python_code

# ==========================
# 4.16 周四：定义工具
# ==========================
@tool
def get_current_time() -> str:
    """
    获取当前日期和时间。
    注意：只有在用户明确要求提供与代码审查相关的实时时间时（例如：需要为日志建议添加时间戳、判断代码中DateTime.Now的使用场景），才可以使用此工具。
    对于普通的“现在几点”闲聊问题，直接拒绝回答，表明自己是代码审查助手。
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

tools = [get_current_time, calculator, execute_python_code]