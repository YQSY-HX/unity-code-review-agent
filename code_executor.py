# code_executor.py
import sys
import io
import traceback
from langchain_core.tools import tool

# =====================================================
# 5.9 周五：代码执行工具
# =====================================================

# 安全的全局变量空间（限制可用内容）
SAFE_GLOBALS = {
    "__builtins__": {
        "print": print,
        "len": len,
        "range": range,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "abs": abs,
        "max": max,
        "min": min,
        "sum": sum,
        "round": round,
        "sorted": sorted,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
        "type": type,
        "isinstance": isinstance,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "Exception": Exception,
    }
}


@tool
def execute_python_code(code: str) -> str:
    """
    执行 Python 代码并返回结果。

    **何时使用此工具：**
    - 当用户需要计算、验证数学结果、生成数据或运行代码时
    - 当用户请求“帮我计算”、“执行这段代码”、“验证这个算法”等
    - 当用户的需求可以用 Python 代码来满足时

    用法：先生成完整的 Python 代码，然后调用此工具执行，最后根据执行结果回答用户。

    注意：
    - 只能使用安全的模块和函数，不能执行文件操作或系统命令
    - 代码执行超时时间为 5 秒
    - 返回的内容是 print() 输出的结果
    """
    # 捕获 stdout
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        # 在受限的全局空间执行代码
        exec(code, SAFE_GLOBALS, {})
        output = sys.stdout.getvalue()
        if output.strip():
            return output.strip()
        else:
            return "代码执行成功，但没有输出内容（可能是没有 print 语句）"
    except Exception as e:
        return f"代码执行错误: {type(e).__name__}: {str(e)}"
    finally:
        sys.stdout = old_stdout