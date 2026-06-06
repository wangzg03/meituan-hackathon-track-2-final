from typing import List, Dict
import time


class TurnLogger:
    """对话日志记录器，支持统一对话表示"""
    
    def __init__(self):
        self.history: List[Dict] = []
        self._dialog_id: str = None
    
    def set_dialog_id(self, dialog_id: str):
        """设置对话 ID，用于标准化输出"""
        self._dialog_id = dialog_id
    
    def add_turn(self, model_msg: str, user_msg: str):
        """添加一轮对话，同时记录元数据"""
        turn = {
            "model": model_msg,
            "user": user_msg,
            "turn_id": len(self.history) + 1,
            "timestamp": time.time()
        }
        self.history.append(turn)
    
    def get_history(self) -> List[Dict]:
        """返回对话历史（兼容原有格式）"""
        return self.history
    
    def get_history_with_metadata(self) -> List[Dict]:
        """返回带元数据的对话历史"""
        return self.history
    
    def clear(self):
        self.history = []
        self._dialog_id = None
    
    def get_dialog_id(self) -> str:
        return self._dialog_id
    
    def get_last_model_message(self) -> str:
        """获取最后一轮客服消息"""
        if self.history:
            return self.history[-1].get("model", "")
        return ""
    
    def get_last_user_message(self) -> str:
        """获取最后一轮用户消息"""
        if self.history:
            return self.history[-1].get("user", "")
        return ""