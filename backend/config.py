import os
from dotenv import load_dotenv

# 加载环境变量配置文件
load_dotenv()

class Config:
    # 模型API的基础URL地址
    BASE_URL = os.getenv("BASE_URL")
    # API访问密钥
    API_KEY = os.getenv("API_KEY")
    # 使用的模型名称
    MODEL_NAME = os.getenv("MODEL_NAME")
    # 模型生成温度参数，控制输出随机性，范围0-1，值越小越确定
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.1))
    # 单次请求的最大token数限制
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 1024))
    # 单轮对话的最大回合数上限
    MAX_DIALOGUE_TURNS = int(os.getenv("MAX_DIALOGUE_TURNS", 20))
    # 每次评测任务的执行轮数
    EVALUATION_ROUNDS = int(os.getenv("EVALUATION_ROUNDS", 1))
    # API请求之间的时间间隔（秒），用于控制请求频率
    REQUEST_INTERVAL = float(os.getenv("REQUEST_INTERVAL", 1.0))
    # 请求失败后的最大重试次数
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))

# 创建配置实例供其他模块使用
config = Config()