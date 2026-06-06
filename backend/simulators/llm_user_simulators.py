import random
import logging
import json
import os
from models.llm_client import LLMClient
from .base_simulator import BaseUserSimulator

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
PERSONA_FILE = os.path.join(PROJECT_ROOT, "param_setting", "personas.json")

def load_persona_templates():
    if os.path.exists(PERSONA_FILE):
        with open(PERSONA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        logger.warning(f"Persona 文件不存在: {PERSONA_FILE}")
        return {}

CHARACTER_TEMPLATES = load_persona_templates()


class UserState:
    def __init__(self):
        self.last_user_msg = ""
        self.last_model_msg = ""
        self.consecutive_repeat_requests = 0
        self.consecutive_interrupts = 0
        self.user_asked_repeat_last_turn = False

    def update(self, user_msg: str, model_msg: str):
        repeat_keywords = ["没听清", "再说一遍", "你刚说啥", "等一下", "我没听清", "打断一下", "诶等等", "你刚说啥？", "再说一次"]
        self.user_asked_repeat_last_turn = any(kw in user_msg for kw in repeat_keywords)
        if self.user_asked_repeat_last_turn:
            self.consecutive_repeat_requests += 1
        else:
            self.consecutive_repeat_requests = 0

        if any(kw in user_msg for kw in ["等一下", "打断一下", "诶等等"]):
            self.consecutive_interrupts += 1
        else:
            self.consecutive_interrupts = 0

        self.last_user_msg = user_msg
        self.last_model_msg = model_msg

    def should_avoid_complaint_on_repeat(self, current_model_msg: str, last_model_msg: str) -> bool:
        if not self.user_asked_repeat_last_turn:
            return False
        if current_model_msg == last_model_msg:
            return True
        return False


class LLMUserSimulator(BaseUserSimulator):
    def __init__(self, role, name=None, max_turns=10, interrupt_prob=0.001, temperature=0.8, personality=None):
        self.llm = LLMClient()
        self.role = role
        self.max_turns = max_turns
        self.interrupt_prob = interrupt_prob
        self.temperature = temperature
        self.turn_count = 0
        self.repeat_question_count = 0
        self.user_state = UserState()

        valid_personalities = list(CHARACTER_TEMPLATES.get(role, {}).keys())
        if not valid_personalities:
            raise ValueError(f"角色 {role} 在 personas.json 中没有定义任何人格")

        if personality and personality != "random" and personality in valid_personalities:
            self.personality = personality
        else:
            self.personality = random.choice(valid_personalities)

        self.persona_config = CHARACTER_TEMPLATES[role][self.personality].copy()
        if name is not None:
            self.persona_config["name"] = name

        self.persona_config.setdefault("name", "未知用户")
        self.persona_config.setdefault("role", "骑手" if role == "rider" else "机构负责人")
        self.persona_config.setdefault("background", {})
        self.persona_config.setdefault("personality", {})
        self.persona_config.setdefault("circumstances", {})
        self.persona_config.setdefault("rules", {})
        self.persona_config.setdefault("language", {})

        self._build_persona_attributes()
        self.system_prompt = self._build_system_prompt()
        logger.info(f"初始化 {role} 模拟器，姓名={self.persona_config['name']}，人格={self.personality}")

    def _build_persona_attributes(self):
        self.persona_name = self.persona_config.get("name", "未知用户")
        self.persona_role = self.persona_config.get("role", "骑手" if self.role == "rider" else "机构负责人")

        bg = self.persona_config.get("background", {})
        if isinstance(bg, dict):
            bg_parts = []
            if bg.get("entry_time"):
                bg_parts.append(f"入职{bg['entry_time']}")
            if bg.get("daily_work"):
                bg_parts.append(f"日常工作：{bg['daily_work']}")
            if bg.get("contract_experience"):
                bg_parts.append(f"合同经历：{bg['contract_experience']}")
            if bg.get("economic_status"):
                bg_parts.append(f"经济状况：{bg['economic_status']}")
            self.persona_background = "。".join(bg_parts) if bg_parts else "无具体背景信息。"
        else:
            self.persona_background = str(bg) if bg else "无具体背景信息。"

        pers = self.persona_config.get("personality", {})
        if isinstance(pers, dict):
            pers_parts = []
            if pers.get("core_thought"):
                pers_parts.append(f"核心想法：{pers['core_thought']}")
            if pers.get("communicate_habit"):
                pers_parts.append(f"沟通习惯：{pers['communicate_habit']}")
            if pers.get("decision_logic"):
                pers_parts.append(f"决策逻辑：{pers['decision_logic']}")
            self.persona_personality = "。".join(pers_parts) if pers_parts else "性格普通。"
        else:
            self.persona_personality = str(pers) if pers else "性格普通。"

        circ = self.persona_config.get("circumstances", {})
        if isinstance(circ, dict):
            circ_parts = []
            if circ.get("current_time"):
                circ_parts.append(f"当前时间：{circ['current_time']}")
            if circ.get("on_hand_status"):
                circ_parts.append(f"手头状态：{circ['on_hand_status']}")
            if circ.get("demand"):
                circ_parts.append(f"需求：{circ['demand']}")
            self.persona_circumstances = "。".join(circ_parts) if circ_parts else "正常状态。"
        else:
            self.persona_circumstances = str(circ) if circ else "正常状态。"

        rules = self.persona_config.get("rules", {})
        if isinstance(rules, dict):
            self.reply_rule = rules.get("reply_rule", "正常回应客服的问题。")
            self.end_call_rule = rules.get("end_call_rule", "客服说再见时回应再见。")
            self.forbid_behavior = rules.get("forbid_behavior", "")
            self.acceptance_rule = rules.get("acceptance_rule", "客服给出合理解释后应接受。")
        else:
            self.reply_rule = str(rules) if rules else "正常对话。"

        lang = self.persona_config.get("language", {})
        self.tone = lang.get("tone", "自然随意") if isinstance(lang, dict) else "自然随意"

    def _build_system_prompt(self):
        customer_role = "站长" if self.role == "rider" else "课程平台客服"
        max_len = "20字" if self.role == "rider" else "25字"

        prompt = f"""你是{self.persona_role}{self.persona_name}，正在接听{customer_role}的电话。

【你的情况】
{self.persona_background}
{self.persona_personality}
{self.persona_circumstances}

【对话规则】
- 每次回复不超过{max_len}，口语化，语气{self.tone}。
- {self.reply_rule}
- {self.end_call_rule}
{f'- {self.forbid_behavior}' if self.forbid_behavior else ''}
- {self.acceptance_rule}

【绝对禁止】
- 说出任何操作指导（如“点击”、“选择”、“保存”、“勾选”、“切换”）。
- 说出任何技术实现（如“后台配置”、“线路切换”、“API”）。
- 替客服回答操作类问题（如“怎么开通”、“怎么配置”）。
- 重复客服刚说过的话。
- 说出帮客服查询类似话语。
- 说出只有客服知道的信息。

现在开始对话。只输出纯文本，不加括号或星号。"""
        return prompt

    def _filter_user_reply(self, reply: str) -> str:
        """代码层过滤违规内容"""
        forbidden_patterns = [
            "点击", "选择", "保存", "勾选", "切换", "输入", "进入", "打开",
            "后台配置", "线路切换", "API", "服务商", "平台管理", "我的", "设置",
            "您需要", "您可以", "请您", "建议您", "请问您", "先帮您",
            "我确认后", "我帮您开通", "我查一下", "我教您"
        ]
        for pat in forbidden_patterns:
            if pat in reply:
                logger.warning(f"用户模拟器输出违规内容: {reply}")
                if self.role == "rider":
                    return "嗯。"
                else:
                    return "然后呢？" if ("?" in reply or "？" in reply) else "好的。"
        # 防止多个问句
        if reply.count("？") > 1 or reply.count("?") > 1:
            reply = reply.split("？")[0] + "？" if "？" in reply else reply.split("?")[0] + "?"
        return reply

    def get_name(self) -> str:
        return self.persona_config["name"]

    def get_response(self, model_message: str, dialogue_history: list) -> str:
        self.turn_count += 1

        if dialogue_history:
            last_turn = dialogue_history[-1]
            last_user = last_turn.get("user", "")
            last_model = last_turn.get("model", "")
            self.user_state.update(last_user, last_model)
        else:
            self.user_state.update("", "")

        # 打断逻辑
        if self.turn_count > 1 and random.random() < self.interrupt_prob:
            if self.user_state.consecutive_repeat_requests < 1:
                interruptions = ["等一下，我没听清", "你刚说啥？", "打断一下", "诶等等"]
                self.user_state.consecutive_repeat_requests += 1
                return random.choice(interruptions)
            else:
                self.user_state.consecutive_repeat_requests = 0

        # 检测再见
        if any(word in model_message for word in ["再见", "挂断", "稍后再打"]):
            return "好的，再见。"

        # 骑手特殊逻辑
        if self.role == "rider":
            think_count = sum(1 for turn in dialogue_history if "我再想想" in turn.get("user", ""))
            if think_count >= 2:
                return random.choice(["得嘞，我去跑", "今天真不行，站长"])

        # 客服重复检测
        if len(dialogue_history) >= 2:
            last_user_msg = dialogue_history[-1].get("user", "")
            last_model = dialogue_history[-1].get("model", "")
            prev_model = dialogue_history[-2].get("model", "")
            repeat_keywords = ["没听清", "再说一遍", "你刚说啥", "等一下", "我没听清", "打断一下", "诶等等", "你刚说啥？", "再说一次"]
            user_asked_repeat = any(kw in last_user_msg for kw in repeat_keywords)
            if last_model == prev_model and last_model:
                if user_asked_repeat:
                    logger.info("用户要求重复后客服合理重复")
                    return "嗯，这回听清了。" if self.role == "rider" else "好的，您继续。"
                else:
                    self.user_state.consecutive_repeat_requests = 0
                    if self.role == "manager":
                        return "您怎么又说一样的话？我们继续吧。"
                    else:
                        return "怎么又说一遍？说重点吧。"

        # 正常生成
        messages = [{"role": "system", "content": self.system_prompt}]
        for turn in dialogue_history:
            messages.append({"role": "assistant", "content": turn.get("model", "")})
            messages.append({"role": "user", "content": turn.get("user", "")})
        messages.append({"role": "assistant", "content": model_message})

        reply = self.llm.chat(messages, temperature=self.temperature)
        if not reply:
            reply = "嗯。" if self.role == "rider" else "然后呢？"

        # 防止复制客服消息
        if reply.strip() == model_message.strip():
            logger.warning(f"用户模拟器完全复制客服消息，已替换")
            return "嗯。" if self.role == "rider" else "然后呢？"

        # 清洗括号
        if any(c in reply for c in ["(", ")", "（", "）"]):
            reply = reply.replace("(", "").replace(")", "").replace("（", "").replace("）", "")
            if not reply.strip():
                reply = "嗯。" if self.role == "rider" else "然后呢？"

        # 连续问句处理
        if reply == "然后呢？":
            self.repeat_question_count = getattr(self, 'repeat_question_count', 0) + 1
            if self.repeat_question_count >= 2:
                logger.warning(f"用户连续{self.repeat_question_count}次问'然后呢？'")
                self.user_state.consecutive_repeat_requests = 0
                return "你没回答我，算了吧，再见。"
        else:
            self.repeat_question_count = 0

        # 代码层过滤
        # reply = self._filter_user_reply(reply)
        self.user_state.consecutive_repeat_requests = 0
        return reply