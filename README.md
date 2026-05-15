# 🧠 Unity C# 代码审查 Agent

> 基于 FastAPI + LangGraph + DeepSeek 的智能代码审查服务，可接入 Unity 编辑器或 CI/CD 流水线。

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-green?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangChain-0.3+-orange?style=flat-square" alt="LangChain">
  <img src="https://img.shields.io/badge/DeepSeek-API-purple?style=flat-square" alt="DeepSeek">
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License">
</p>

## ✨ 核心特性

- 🔍 **代码审查**：自动检查 C# 代码规范、性能问题、面向对象设计
- 🧠 **ReAct Agent**：自主决策、工具调用（时间/计算器/代码执行/联网搜索）
- 📊 **结构化输出**：Pydantic 约束 JSON 格式，可被下游工具直接解析
- 💬 **多轮对话记忆**：Memory + Session 隔离
- ⚡ **流式输出**：SSE 实现打字机效果
- 🛡️ **工程化加固**：容错清洗、重试机制、统一异常处理、安全沙箱
- 🌐 **已部署上线**：Railway（后端）+ Netlify（前端），公网可访问

## 🚀 快速启动

```bash
git clone https://github.com/YQSY-HX/unity-code-review-agent.git
cd unity-code-review-agent
pip install -r requirements.txt
export DEEPSEEK_API_KEY="你的API密钥"
python main.py
# 访问 http://127.0.0.1:10000/docs