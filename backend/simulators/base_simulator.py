from abc import ABC, abstractmethod

class BaseUserSimulator(ABC):
    """用户模拟器基类"""
    
    @abstractmethod
    def get_response(self, model_message: str, dialogue_history: list) -> str:
        """根据模型的上一条消息和对话历史，返回模拟用户的回复"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """返回模拟器名称"""
        pass