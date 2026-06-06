import re
import string
import logging
from typing import List, Dict, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

def count_chars_no_punctuation(text: str) -> int:
    """去除中英文标点符号后的字符数"""
    # 移除英文标点
    translator = str.maketrans('', '', string.punctuation)
    text_no_punct = text.translate(translator)
    # 移除常见中文标点
    chinese_punct = "，。！？；：“”‘’、"
    for ch in chinese_punct:
        text_no_punct = text_no_punct.replace(ch, '')
    return len(text_no_punct.strip())


class MetricsCalculator:
    """客观硬约束评估器（字数、重复、禁用词、特殊场景）"""

    @staticmethod
    def compute_constraint_score(dialogue_history: List[Dict], scenario: str) -> Tuple[float, List[str]]:
        """
        返回 (约束遵守得分0-1, 违规列表)
        """
        return MetricsCalculator._check_constraints(dialogue_history, scenario)

    @staticmethod
    def _check_constraints(dialogue_history: List[Dict], scenario: str) -> Tuple[float, List[str]]:
        violations = []
        total_turns = len(dialogue_history)
        if total_turns == 0:
            return 1.0, []

        model_turns = [turn.get("model", "") for turn in dialogue_history if "model" in turn]
        max_len = 30 if scenario == "delivery" else 20

        # 1. 字数违规（不包含标点符号，外卖开场白跳过）
        len_violations = 0
        for i, msg in enumerate(model_turns):
            if scenario == "delivery" and i == 0:  # 开场白跳过检查
                continue
            char_count = count_chars_no_punctuation(msg)
            # 允许上浮5字
            if char_count > max_len + 5:
                len_violations += 1
                violations.append(f"第{i+1}轮字数{char_count}超过限制{max_len}（允许{max_len}+5）")
        len_score = 1.0 - (len_violations / max(1, total_turns))

        # 2. 重复检测（完全重复 + 相似度>0.8）
        repeat_count = 0
        for i in range(1, len(model_turns)):
            prev = model_turns[i-1]
            curr = model_turns[i]
            if curr == prev:
                repeat_count += 1
                violations.append(f"第{i+1}轮完全重复上一轮")
            elif SequenceMatcher(None, curr, prev).ratio() > 0.8:
                repeat_count += 1
                violations.append(f"第{i+1}轮与上一轮高度相似（{curr}）")
        repeat_score = 1.0 - (repeat_count / max(1, total_turns))

        # 3. 禁用语气词 / 优惠券
        full_text = " ".join(model_turns)
        special_penalty = 0
        bad_words = ["好的", "哈哈", "嘿嘿", "嘻嘻"]
        for bw in bad_words:
            if bw in full_text:
                violations.append(f"使用了禁用语气词 '{bw}'")
                special_penalty += 0.2
                break
        if "优惠券" in full_text or "折扣券" in full_text:
            violations.append("承诺了优惠券")
            special_penalty += 0.3

        # 4. 场景特殊处理
        if scenario == "course":
            user_text = " ".join([turn.get("user", "") for turn in dialogue_history if "user" in turn])
            if "在开车" in user_text or "很忙" in user_text:
                if not any("稍后再打" in msg or "就1分钟" in msg for msg in model_turns):
                    violations.append("用户说忙/开车，未按要求回复'稍后再打'或'就1分钟'")
                    special_penalty += 0.3
        elif scenario == "delivery":
            if any("今天真不行" in turn.get("user", "") for turn in dialogue_history):
                last_model = model_turns[-1] if model_turns else ""
                if not ("注意身体" in last_model or "注意安全" in last_model or "再见" in last_model):
                    violations.append("骑手坚持不配送，最后未安慰或挂断")
                    special_penalty += 0.3

        special_score = max(0, 1.0 - special_penalty)
        total_score = (len_score + repeat_score + special_score) / 3
        return total_score, violations