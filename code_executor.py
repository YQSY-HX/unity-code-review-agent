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
    import signal

    # 捕获 stdout
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    # 超时处理函数
    def timeout_handler(signum,frame):
        raise TimeoutError("代码执行超时（超过5秒）")

    try:
        # 设置 5 秒超时（Windows 上 signal 不可用，直接用 try/except 兜底）
        signal.signal(signal.SIGALRM,timeout_handler)
        signal.alarm(5)


        # 在受限的全局空间执行代码
        exec(code, SAFE_GLOBALS, {})
        output = sys.stdout.getvalue()

        # 取消超时
        signal.alarm(0)

        # 输出长度限制：最多 2000 字符
        if len(output) > 2000:
            output = output[:2000] + "\n...（输出过长，已截断）"

        if output.strip():
            return output.strip()
        else:
            return "代码执行成功，但没有输出内容（可能是没有 print 语句）"
    except TimeoutError:
        return "代码执行超时（超过 5 秒），已自动终止。请检查代码是否有死循环或计算量过大。"
    except Exception as e:
        return f"代码执行错误: {type(e).__name__}: {str(e)}"
    finally:
        sys.stdout = old_stdout