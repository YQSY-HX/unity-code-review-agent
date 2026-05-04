# agent_graph.py
from langgraph.prebuilt import create_react_agent
from agent_tools import tools


# ==========================
# 4.16 周四：构建 ReAct Agent
# ==========================
def get_agent_graph(llm):
    """返回 Agent 图（需要传入 llm 实例）"""
    return create_react_agent(llm, tools)