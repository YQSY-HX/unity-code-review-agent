# search_tool.py
from langchain_core.tools import tool
# from duckduckgo_search import DDGS  DuckDuckGo 搜索后端连接不稳定
from ddgs import DDGS

@tool
def search_web(query: str) -> str:
    """
    在互联网上搜索信息。

    **何时使用此工具：**
    - 当用户询问当前新闻、实时信息、最新数据时
    - 当用户的问题需要联网查询才能准确回答时
    - 当用户询问你的训练数据之外的信息时

    用法：传入搜索关键词，返回前 3 条搜索结果。
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results:
                return f"没有找到关于 '{query}' 的搜索结果。"
            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(f"{i}. {r['title']}\n   {r['body']}\n   {r['href']}")
            return "\n\n".join(formatted)
    except Exception as e:
        return f"搜索失败：{str(e)}"