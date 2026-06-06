# simulators/customer_agent.py (重构版)

from abc import ABC, abstractmethod
from models.llm_client import LLMClient
from param_setting.user_params import user_params

class BaseCustomerAgent(ABC):
    @abstractmethod
    def get_response(self, user_message: str, history: list, state_hint: str = "", scenario: str = "delivery") -> str:
        pass

class LLMCustomerAgent(BaseCustomerAgent):
    def __init__(self, system_prompt: str, name: str = "客服", temperature: float = 0.7):
        self.llm = LLMClient()
        self.base_system_prompt = system_prompt  # 包含占位符的原始 prompt
        self.name = name
        self.temp = temperature
        # 加载配送场景参数（用于替换 prompt 中的变量）
        self.delivery_params = user_params.get_delivery_params()
        self.X = self.delivery_params.get("X", 15)
        self.Y = self.delivery_params.get("Y", 15)
        self.reward = self.delivery_params.get("reward", 2)
        self.W = self.delivery_params.get("W", 3)
        self.Z = self.delivery_params.get("Z", 20)

    def _replace_prompt_vars(self, prompt: str, scenario: str, rider_name: str = "") -> str:
        """替换 prompt 中的变量占位符（如 ${X}, ${rider_name}）"""
        if scenario == "delivery":
            prompt = prompt.replace("${X}", str(self.X))
            prompt = prompt.replace("${Y}", str(self.Y))
            prompt = prompt.replace("${reward}", str(self.reward))
            prompt = prompt.replace("${W}", str(self.W))
            prompt = prompt.replace("${Z}", str(self.Z))
            prompt = prompt.replace("${rider_name}", rider_name)
        return prompt

    def get_response(self, user_message: str, history: list, state_hint: str = "", scenario: str = "delivery", rider_name: str = "") -> str:
        # 1. 准备系统提示
        system_prompt = self.base_system_prompt
        # 替换变量
        system_prompt = self._replace_prompt_vars(system_prompt, scenario, rider_name)
        # 注入流程状态和已知信息
        system_prompt = system_prompt.replace("{{flow_state}}", state_hint)
        # 注意：known_info 已在 state_hint 中包含（通过 _extract_known_info），无需单独替换
        
        # 2. 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加对话历史（最近 8 轮）
        for turn in history[-8:]:
            if turn.get("user"):
                messages.append({"role": "user", "content": turn["user"]})
            if turn.get("model"):
                messages.append({"role": "assistant", "content": turn["model"]})
        
        # 添加当前用户消息
        if user_message:
            messages.append({"role": "user", "content": user_message})
        
        # 3. 调用 LLM
        reply = self.llm.chat(messages, temperature=self.temp)
        
        # 4. 后处理：去除可能的前后空白，确保非空
        if not reply or not reply.strip():
            reply = "请问您还有什么问题吗？"
        
        return reply