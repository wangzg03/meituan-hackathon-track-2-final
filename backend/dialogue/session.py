from typing import List, Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class StepStatus(Enum):
    NOT_STARTED = 0
    COMPLETED = 1

class Flow:
    def __init__(self, name: str, steps: List[str]):
        self.name = name
        self.steps = steps.copy()  # 副本，避免外部修改
        self.current_step = 0
        self.status = [StepStatus.NOT_STARTED] * len(steps)
        self.advanced_completed = [False] * len(steps)
        self.llm_client = None
        self.step_start_turn = {i: 0 for i in range(len(steps))}
        self._init_step_rules()

    def _init_step_rules(self):
        if self.name == "course":
            self.step_rules = {
                "身份确认": ["请问您是负责人", "是负责人吗", "您是贵培训机构", "机构负责人", "负责人吗"],
                "确认知情": ["知道后台已开启", "知道低延迟", "后台已开启低延迟", "您知道吗", "是否知情", "知道后台临时开启"],
                "解释标准与低延迟区别及价格": ["标准延迟", "低延迟延迟", "延迟约", "标准直播便宜", "低延迟略高", "区别", "价格", "标准直播费用低"],
                "询问发布方式并引导": ["通过什么系统", "哪种系统", "Web控制台", "校务系统", "SaaS", "发课", "系统发课"],
                "检查学员端费用": ["学员端收费", "收费规则设置", "费用设置", "设置了费用吗", "学员端费用", "收费规则"],
                "企业微信添加": ["企业微信", "加微信", "稍后加您", "添加企业微信", "通过验证"],
                "结束祝福": ["祝您课程顺利", "再见", "招生满满"]
            }
        else:
            self.step_rules = {
                "告知合同生效并询问配送意愿": ["合同已生效", "可以正常配送", "合同生效", "今天可以配送", "飞毛腿合同", "正常配送吗"],
                "询问合同类型": ["单日合同", "多日合同", "报名的是", "合同类型", "单日还是多日"],
                "说明单日/多日要求": ["单日合同需", "多日合同每天", "至少完成", "名额被占", "每天至少", "合同需生效当天"],
                "说明排名规则": ["排名录取", "按排名", "少拒单", "恶劣天气", "排名规则", "飞毛腿按排名"],
                "安全提醒与鼓励": ["注意安全", "有问题随时联系", "路上注意安全", "安全提醒"],
                "结束祝福": ["跑单顺利", "再见"]
            }

    def set_llm_client(self, llm_client):
        self.llm_client = llm_client

    def get_step_phrase(self, step_name: str) -> str:
        if self.name == "course":
            phrases = {
                "身份确认": "您好，请问您是负责人吗？",
                "确认知情": "您知道后台已为您开启低延迟线路吗？",
                "解释标准与低延迟区别及价格": "标准延迟5-10秒，低延迟1-2秒。",
                "询问发布方式并引导": "您通过哪种系统发课？",
                "检查学员端费用": "学员端收费规则设置好了吗？",
                "企业微信添加": "稍后加您企业微信，请通过。",
                "结束祝福": "祝您课程顺利，再见。"
            }
        else:
            phrases = {
                "告知合同生效并询问配送意愿": "请问今天可以正常配送吗？",
                "询问合同类型": "请问是单日合同还是多日合同？",
                "说明单日/多日要求": "每天至少完成5单，否则合同受影响。",
                "说明排名规则": "飞毛腿按排名录取，少拒单超时。",
                "安全提醒与鼓励": "路上注意安全，有问题随时联系。",
                "结束祝福": "祝您跑单顺利，再见。"
            }
        return phrases.get(step_name, "我们继续。")

    def _check_step_completed_by_rule(self, model_message: str, step_name: str) -> bool:
        if step_name not in self.step_rules:
            return False
        msg_lower = model_message.lower()
        for keyword in self.step_rules[step_name]:
            if keyword.lower() in msg_lower:
                logger.debug(f"[规则匹配] 步骤 '{step_name}' 匹配关键词 '{keyword}'")
                return True
        return False

    def _check_step_completed_by_llm(self, model_message: str, step_name: str, history: List[Dict] = None) -> bool:
        if not self.llm_client:
            return bool(model_message and len(model_message) > 5)
        prompt = f"""判断以下客服消息是否已经完成了步骤“{step_name}”。

步骤名称：{step_name}
标准话术参考：{self.get_step_phrase(step_name)}

客服最新消息："{model_message}"

判断标准（严格遵循）：
- 如果客服消息明确包含了该步骤的核心询问或告知（允许不同措辞），输出“是”。
- 如果客服消息只是回应其他问题、道歉、或说“抱歉重复了”等无关内容，输出“否”。
- 只输出“是”或“否”。

具体示例：
- 步骤“确认知情”的标准话术是“您知道后台已为您开启低延迟线路吗？”如果客服说“您之前用的标准直播，后台已为您切到低延迟，您知道吗？” → 是
- 如果客服只说“抱歉，我重复了” → 否
"""
        try:
            resp = self.llm_client.chat([{"role": "user", "content": prompt}], temperature=0.0)
            return resp.strip().lower() == "是"
        except Exception as e:
            logger.warning(f"LLM 判断步骤完成失败: {e}")
            return False

    def update(self, model_message: str, turn_number: int, history: List[Dict] = None) -> bool:
        if self.current_step >= len(self.steps):
            return False
        if self.status[self.current_step] == StepStatus.COMPLETED:
            while self.current_step < len(self.steps) and self.status[self.current_step] == StepStatus.COMPLETED:
                self.current_step += 1
            return True

        step_name = self.steps[self.current_step]
        if self.step_start_turn[self.current_step] == 0:
            self.step_start_turn[self.current_step] = turn_number

        completed = self._check_step_completed_by_rule(model_message, step_name)
        if completed:
            logger.info(f"[Flow] 步骤完成(规则匹配): {step_name}")
        else:
            completed = self._check_step_completed_by_llm(model_message, step_name, history)
            if completed:
                logger.info(f"[Flow] 步骤完成(LLM判断): {step_name}")
            else:
                logger.debug(f"[Flow] 步骤未完成: {step_name}")

        if completed:
            self.status[self.current_step] = StepStatus.COMPLETED
            self.current_step += 1
            return True
        return False

    def advance_complete(self, step_index: int) -> bool:
        if 0 <= step_index < len(self.steps) and self.status[step_index] == StepStatus.NOT_STARTED:
            self.status[step_index] = StepStatus.COMPLETED
            self.advanced_completed[step_index] = True
            if step_index == self.current_step:
                while self.current_step < len(self.steps) and self.status[self.current_step] == StepStatus.COMPLETED:
                    self.current_step += 1
            logger.info(f"[Flow] 提前完成步骤 {step_index}: {self.steps[step_index]}")
            return True
        return False

    def get_next_step(self) -> Optional[str]:
        for i in range(self.current_step, len(self.steps)):
            if self.status[i] == StepStatus.NOT_STARTED:
                return self.steps[i]
        return None

    def is_completed(self) -> bool:
        return self.current_step >= len(self.steps) or all(s == StepStatus.COMPLETED for s in self.status)

    def get_uncompleted_steps(self) -> List[str]:
        return [self.steps[i] for i, s in enumerate(self.status) if s == StepStatus.NOT_STARTED]

    def get_completed_steps(self) -> List[str]:
        return [self.steps[i] for i, s in enumerate(self.status) if s == StepStatus.COMPLETED]

    def get_completion_rate(self) -> float:
        completed = sum(1 for s in self.status if s == StepStatus.COMPLETED)
        return completed / len(self.steps) if self.steps else 1.0


# 步骤模板（不再是全局 Flow 实例）
DELIVERY_STEPS = [
    "告知合同生效并询问配送意愿",
    "询问合同类型",
    "说明单日/多日要求",
    "说明排名规则",
    "安全提醒与鼓励",
    "结束祝福"
]

COURSE_STEPS = [
    "身份确认",
    "确认知情",
    "解释标准与低延迟区别及价格",
    "询问发布方式并引导",
    "检查学员端费用",
    "企业微信添加",
    "结束祝福"
]


class Session:
    def __init__(self, scenario: str, llm_client=None):
        self.scenario = scenario
        self.history: List[Dict] = []
        # 每次创建全新的 Flow 实例（基于步骤列表），而不是复用全局单例
        if scenario == "delivery":
            self.flow = Flow("delivery", DELIVERY_STEPS)
        else:
            self.flow = Flow("course", COURSE_STEPS)
        self.flow.set_llm_client(llm_client)

        self.user_repeat_counter: Dict[str, int] = {}
        self.last_user_message = ""
        self.consecutive_meaningless = 0
        self.mentioned_steps: Dict[str, int] = {}
        self.llm_client = llm_client
        self.user_end_intent_count = 0
        self.consecutive_short_replies = 0
        self.turn_count = 0

    def add_turn(self, model_msg: str, user_msg: str):
        self.turn_count += 1
        self.history.append({"model": model_msg, "user": user_msg})
        self.flow.update(model_msg, self.turn_count, self.history)

        if user_msg == self.last_user_message and user_msg != "":
            self.user_repeat_counter[user_msg] = self.user_repeat_counter.get(user_msg, 0) + 1
        else:
            self.user_repeat_counter = {user_msg: 1} if user_msg else {}
        self.last_user_message = user_msg

        meaningless = ["然后呢？", "诶等等", "等一下", "没听清", "再说一遍", "你刚说啥", "沉默", ""]
        if user_msg.strip() in meaningless:
            self.consecutive_meaningless += 1
        else:
            self.consecutive_meaningless = 0

        end_keywords = ["挂了", "回头再说", "再联系", "忙", "先挂了"]
        if any(kw in user_msg for kw in end_keywords):
            self.user_end_intent_count += 1
        else:
            if len(user_msg) > 4 and not any(kw in user_msg for kw in end_keywords):
                self.user_end_intent_count = max(0, self.user_end_intent_count - 1)

    def detect_advanced_completion(self, model_msg: str, user_msg: str) -> Optional[int]:
        uncompleted_indices = [i for i, s in enumerate(self.flow.status) if s == StepStatus.NOT_STARTED]
        if not uncompleted_indices:
            return None

        if not self.llm_client:
            return None

        for idx in uncompleted_indices:
            if idx <= self.flow.current_step:
                continue
            step_name = self.flow.steps[idx]

            user_intent_prompt = f"""用户说：“{user_msg}”
用户是否在询问或提及步骤“{step_name}”的相关内容？只回答“是”或“否”。"""
            try:
                resp = self.llm_client.chat([{"role": "user", "content": user_intent_prompt}], temperature=0.0)
                if resp.strip().lower() != "是":
                    continue
            except:
                continue

            answer_prompt = f"""步骤：“{step_name}”
用户问题：“{user_msg}”
客服回答：“{model_msg}”

客服的回答是否已经正面、完整地解决了用户对该步骤的疑问？（不是推诿、不是简单说“稍后回电”或“短信发送”）只输出“是”或“否”。"""
            try:
                resp = self.llm_client.chat([{"role": "user", "content": answer_prompt}], temperature=0.0)
                if resp.strip().lower() == "是":
                    logger.info(f"[Session] LLM 判断：用户提前询问步骤{idx}，客服已回答，标记为完成")
                    return idx
            except:
                continue
        return None

    def try_advance_completion(self, model_msg: str, user_msg: str) -> bool:
        idx = self.detect_advanced_completion(model_msg, user_msg)
        if idx is not None:
            return self.flow.advance_complete(idx)
        return False

    def _extract_known_info(self) -> List[str]:
        known = []
        for turn in self.history:
            user_msg = turn.get("user", "")
            if not user_msg:
                continue
            if self.scenario == "delivery":
                if "单日" in user_msg or "单日合同" in user_msg:
                    known.append("用户已确认是单日合同")
                elif "多日" in user_msg or "多日合同" in user_msg:
                    known.append("用户已确认是多日合同")
                if any(kw in user_msg for kw in ["可以配送", "能跑", "行", "好", "得嘞"]):
                    known.append("用户已同意配送")
                elif any(kw in user_msg for kw in ["不能配送", "不想跑", "跑不了", "不行"]):
                    known.append("用户已拒绝配送")
                if "扣款" in user_msg or "扣罚" in user_msg:
                    known.append("用户已问过扣款规则")
                if "奖励" in user_msg:
                    known.append("用户已问过奖励")
                if "名额" in user_msg:
                    known.append("用户已问过名额问题")
                if "退出" in user_msg:
                    known.append("用户已问过退出规则")
            elif self.scenario == "course":
                if "Web控制台" in user_msg:
                    known.append("用户已告知使用Web控制台")
                elif "校务系统" in user_msg or "校务系统A" in user_msg:
                    known.append("用户已告知使用校务系统A")
                elif "SaaS" in user_msg or "SaaS系统B" in user_msg:
                    known.append("用户已告知使用SaaS系统B")
                if any(kw in user_msg for kw in ["我是负责人", "是我", "对的"]):
                    known.append("用户已确认自己是负责人")
                if "注意到" in user_msg or "看到" in user_msg:
                    known.append("用户已回应知情问题")
                if "收费" in user_msg or "价格" in user_msg:
                    known.append("用户已问过价格")
                if "学员端费用" and "能看到低延迟选项" in user_msg:
                    known.append("用户已问过学员端费用")
                if "企业微信" in user_msg or "加微信" in user_msg:
                    known.append("用户已回应企业微信添加")
        unique = []
        for item in known:
            if item not in unique:
                unique.append(item)
        return unique

    def get_flow_state_hint(self) -> str:
        completed = self.flow.get_completed_steps()
        uncompleted = self.flow.get_uncompleted_steps()
        next_step = self.flow.get_next_step()

        lines = []
        if completed:
            lines.append(f"已完成步骤：{', '.join(completed)}")
        if uncompleted:
            lines.append(f"未完成步骤（按顺序）：{', '.join(uncompleted)}")
            lines.append(f"你的下一句回复必须输出下一步话术：{next_step}")
        else:
            lines.append("所有步骤已完成，请礼貌结束通话。")

        known = self._extract_known_info()
        if known:
            lines.append(f"已获取信息：{'; '.join(known)}")
            lines.append("绝对禁止重复询问或告知以上已获取的信息或重复步骤。")

        repeat_hint = self.get_repeat_hint()
        if repeat_hint:
            lines.append(repeat_hint)

        if self.user_end_intent_count >= 2:
            lines.append(f"用户已表达结束意图 {self.user_end_intent_count} 次，请尽快完成剩余步骤后结束。")

        return "\n".join(lines)

    def get_repeat_hint(self) -> str:
        repeated = [q for q, cnt in self.user_repeat_counter.items() if cnt >= 2]
        if repeated:
            return f"注意：用户已经重复提问“{repeated[0]}”，请不要再重复相同的回答，尝试提供新信息或引导结束。"
        return ""