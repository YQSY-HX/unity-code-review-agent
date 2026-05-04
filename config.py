# config.py
import os


class Config:
    """项目配置类，支持环境变量覆盖"""

    # DeepSeek API 配置
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    # 服务配置
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "8080"))

    # 跨域配置
    FRONTEND_URL = os.getenv("FRONTEND_URL", "https://你的前端项目名.vercel.app")

    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


config = Config()