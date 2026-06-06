# orchestrator.py (最终稳定版：强制防止提前结束)

from typing import List, Dict, Optional
import logging
from dialogue.turn_logger import TurnLogger
from simulators.base_simulator import BaseUserSimulator
from simulators.customer_agent import BaseCustomerAgent
from .session import Session

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, customer_agent: BaseCustomerAgent, user_simulator: BaseUserSimulator,
                 max_turns: int = 10, early_stop_keywords: List[str] = None, scenario: str = "delivery"):
        self.customer = customer_agent
        self.user = user_simulator
        self.max_turns = max_turns
        self.stop_words = early_stop_keywords or ["再见", "挂断", "稍后再打"]
        self.logger = TurnLogger()
        self.scenario = scenario
        self.session = None

    def run(self, init_customer_message: str = None) -> List[Dict]:
        self.logger.clear()
        self.session = Session(self.scenario, llm_client=getattr(self.customer, 'llm', None))

        rider_name = ""
        if self.scenario == "delivery" and hasattr(self.user, 'get_name'):
            rider_name = self.user.get_name().split('(')[0].strip()

        # 第一轮
        if init_customer_message:
            customer_reply = init_customer_message
        else:
            state_hint = self.session.get_flow_state_hint()
            customer_reply = self.customer.get_response(
                "", [], state_hint=state_hint, scenario=self.scenario, rider_name=rider_name
            )
        self.logger.add_turn(customer_reply, "")
        self.session.add_turn(customer_reply, "")

        turn = 0
        while turn < self.max_turns:
            last_model = self.logger.get_history()[-1]["model"]
            user_reply = self.user.get_response(last_model, self.logger.get_history())
            self.logger.history[-1]["user"] = user_reply
            self.session.add_turn(last_model, user_reply)

            # 用户主动结束
            if any(kw in user_reply for kw in self.stop_words):
                break
            if "开车" in user_reply:
                end_msg = "那稍后再给您打，注意安全。" if self.scenario == "delivery" else "那稍后再打，注意安全。"
                self.logger.add_turn(end_msg, "")
                break
            if any(phrase in user_reply for phrase in ["忙", "开会"]):
                if self.scenario == "course":
                    pass
                else:
                    self.logger.add_turn("好的，那您先忙，再见。", "")
                    break

            # 检测提前完成
            self.session.try_advance_completion(last_model, user_reply)

            # 生成客服回复
            state_hint = self.session.get_flow_state_hint()
            customer_reply = self.customer.get_response(
                user_reply, self.logger.get_history(), state_hint=state_hint,
                scenario=self.scenario, rider_name=rider_name
            )

            # ========== 去重检测 ==========
            if self.logger.history and not self.session.flow.is_completed():
                last_reply = self.logger.history[-1].get("model", "")
                if customer_reply == last_reply:
                    next_step = self.session.flow.get_next_step()
                    if next_step:
                        fallback = self.session.flow.get_step_phrase(next_step)
                        customer_reply = fallback
                        logger.info(f"[去重] 重复回复，替换为: {customer_reply}")
                    else:
                        customer_reply = "祝您顺利，再见。" if self.scenario == "delivery" else "祝您顺利，再见。"

            # ========== 核心修复：强制拦截提前结束 ==========
            # 如果客服回复中包含结束词，但流程未完成，则强制替换为下一步话术
            if any(kw in customer_reply for kw in self.stop_words):
                if not self.session.flow.is_completed():
                    next_step = self.session.flow.get_next_step()
                    if next_step:
                        fallback = self.session.flow.get_step_phrase(next_step)
                        customer_reply = fallback
                        logger.warning(f"[流程] 客服提前结束，已强制替换为下一步: {customer_reply}")
                    else:
                        # 没有下一步但流程未完成（罕见），用兜底
                        customer_reply = "请问您还有什么问题吗？"
                        logger.warning("[流程] 流程未完成且无下一步，使用兜底话术")

            self.logger.add_turn(customer_reply, "")
            self.session.add_turn(customer_reply, "")

            # 仅当流程已完成且客服说了结束词时才退出
            if self.session.flow.is_completed() and any(kw in customer_reply for kw in self.stop_words):
                break

            turn += 1

        # 打印统计信息
        flow = self.session.flow
        completed = flow.get_completed_steps()
        uncompleted = flow.get_uncompleted_steps()
        rate = flow.get_completion_rate()
        logger.info("========== 对话统计 ==========")
        logger.info(f"总轮数: {self.session.turn_count}")
        logger.info(f"已完成步骤: {completed}")
        logger.info(f"未完成步骤: {uncompleted}")
        logger.info(f"完成率: {rate:.1%}")
        logger.info(f"是否完成: {flow.is_completed()}")
        if self.logger.get_history():
            logger.info(f"最后客服回复: {self.logger.get_history()[-1].get('model', '')}")
        logger.info("==============================")

        return self.logger.get_history()