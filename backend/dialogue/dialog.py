"""
标准化对话表示
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import json


@dataclass
class Turn:
    """单轮对话数据结构"""
    turn_id: int
    agent: str           # 说话角色: "客服" / "用户"
    content: str
    timestamp: float = field(default_factory=datetime.now().timestamp)
    
    def to_dict(self) -> Dict:
        return {
            "turn_id": self.turn_id,
            "agent": self.agent,
            "content": self.content,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Turn":
        return cls(
            turn_id=data["turn_id"],
            agent=data["agent"],
            content=data["content"],
            timestamp=data.get("timestamp", datetime.now().timestamp())
        )


@dataclass
class Dialog:
    """
    标准化对话表示
    包含对话元数据、角色信息、轮次历史等
    """
    dialog_id: str
    scenario: str                     # 场景名称: "delivery" / "course"
    customer_name: str                # 客服角色名称
    user_name: str                    # 用户角色名称
    turns: List[Turn] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def add_turn(self, agent: str, content: str):
        """添加一轮对话"""
        turn_id = len(self.turns) + 1
        self.turns.append(Turn(turn_id=turn_id, agent=agent, content=content))
    
    def to_dict(self) -> Dict:
        return {
            "dialog_id": self.dialog_id,
            "scenario": self.scenario,
            "customer_name": self.customer_name,
            "user_name": self.user_name,
            "turns": [turn.to_dict() for turn in self.turns],
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Dialog":
        dialog = cls(
            dialog_id=data["dialog_id"],
            scenario=data["scenario"],
            customer_name=data["customer_name"],
            user_name=data["user_name"],
            metadata=data.get("metadata", {})
        )
        for turn_data in data.get("turns", []):
            dialog.turns.append(Turn.from_dict(turn_data))
        return dialog
    
    def to_legacy_history(self) -> List[Dict]:
        """
        转换为原有格式的 history，保持向后兼容
        原有格式: [{"model": "...", "user": "..."}, ...]
        """
        history = []
        for i in range(0, len(self.turns), 2):
            model_turn = self.turns[i]
            user_turn = self.turns[i + 1] if i + 1 < len(self.turns) else None
            turn_dict = {"model": model_turn.content}
            if user_turn:
                turn_dict["user"] = user_turn.content
            else:
                turn_dict["user"] = ""
            history.append(turn_dict)
        return history
    
    @classmethod
    def from_legacy_history(cls, dialog_id: str, scenario: str, 
                            customer_name: str, user_name: str,
                            history: List[Dict]) -> "Dialog":
        """从原有格式的 history 构建 Dialog 对象"""
        dialog = cls(
            dialog_id=dialog_id,
            scenario=scenario,
            customer_name=customer_name,
            user_name=user_name
        )
        for turn in history:
            if turn.get("model"):
                dialog.add_turn(customer_name, turn["model"])
            if turn.get("user"):
                dialog.add_turn(user_name, turn["user"])
        return dialog


class DialogFactory:
    """对话工厂，用于创建标准化的 Dialog 对象"""
    
    @staticmethod
    def create_delivery_dialog(dialog_id: str, history: List[Dict], 
                                rider_name: str = "骑手") -> Dialog:
        """创建外卖场景的标准化 Dialog"""
        return Dialog.from_legacy_history(
            dialog_id=dialog_id,
            scenario="delivery",
            customer_name="站长",
            user_name=rider_name,
            history=history
        )
    
    @staticmethod
    def create_course_dialog(dialog_id: str, history: List[Dict],
                              manager_name: str = "机构负责人") -> Dialog:
        """创建课程场景的标准化 Dialog"""
        return Dialog.from_legacy_history(
            dialog_id=dialog_id,
            scenario="course",
            customer_name="客服",
            user_name=manager_name,
            history=history
        )