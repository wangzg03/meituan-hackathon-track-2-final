import json
import re
import logging
from models.llm_client import LLMClient
from typing import List, Dict
import json_repair
logger = logging.getLogger(__name__)

DEEP_EVALUATION_PROMPT_DELIVERY = """
你是外呼对话质量评估专家。请分析以下【对话记录】，根据【业务指令】给出综合评估。

【业务指令 - 外卖场景】
角色：美团外卖骑手的站长。
任务：致电"飞毛腿"骑手，通知今天合同已成功签署，并提醒完成配送任务。
核心流程：
1. 告知合同生效，询问是否可以配送。
2. 说明单日合同需要连续一定天数完成，否则受影响。
3. 挽留不想配送的，鼓励能配送的，提醒安全。
4. 说明报名按排名，减少拒单/取消/超时，恶劣天气工作有助于保住资格。
关键FAQ：名额可能被占；单日合同须完成X单；多日每天Y单；退出需前一天Z点前APP取消；连续完成W天有奖励。不要求对话内容全覆盖FAQ信息。
约束：每次回复约30字以内（开场白除外，不包含标点符号），避免重复，超职责问“我确认后再回电”，坚持不配送则安慰后挂断。

【宽容评估规则】
1. **信息密度**：允许一句话包含多个必要信息（如合同生效+高峰期要求），不扣自然度分。
2. **挽留策略**：骑手拒绝时，客服可先简单挽留一次，若仍拒绝则允许直接结束，**不要求反复挽留**。
3. **安全提醒**：可在任意合适位置提醒安全（不一定非要最后），不扣流程分。
4. **价格问题**：面对具体价格追问，回复“根据跑单情况计算”或“短信发您”视为合理，**不扣策略灵活性分**。
5. **字数限制**：30字允许±5字浮动（即25-35字）。
6. 当用户对合同真实性提出质疑（如“我没签过合同”）时，评估客服是否能够妥善解释（例如“系统显示您已报名”）
7. 当用户反问客服身份时（如“你是真的站长吗？”），评估客服是否能够恰当回应（如提供工号或确认信息）。
8. 当用户本身对配送有抵制时，评估不要太严苛，但仍保持专业的态度。


【对话记录】
{dialogue}

**重要：输出必须是合法的 JSON 对象，对象内每个键值对之间必须用逗号分隔，字符串内不能有未转义的双引号。不要输出任何其他文字。**
**重要：你必须输出 "readiness_score"（0-100之间的整数）和 "readiness_comment"（字符串，说明是否可以上线及风险点），这两个字段不可省略。**
{{
  "scores": {{
    "task_completion": 0-100,
    "process_adherence": 0-100,
    "naturalness": 0-100,
    "strategy_adaptation": 0-100
  }},
  "overall_score": 0-100,
  "strengths": ["优点1", "优点2"],
  "weaknesses": [
    {{
      "dimension": "naturalness",
      "turn": 2,
      "quote": "机器人原话",
      "reason": "为什么不好",
      "suggestion": "可以怎么说"
    }}
  ],
  "critical_incidents": [
    {{
      "turn": 3,
      "type": "用户拒绝",
      "robot_response": "...",
      "evaluation": "处理得当/不当，因为..."
    }}
  ],
  "improvement_suggestions": [
    "针对系统提示词的建议1",
    "针对模型训练的建议2"
  ],
  "readiness_score": 0-100,
  "readiness_comment": "说明是否可以上线及风险点"
}}
"""

DEEP_EVALUATION_PROMPT_COURSE = """
你是外呼对话质量评估专家。请分析以下【对话记录】，根据【业务指令】给出综合评估。

【业务指令 - 课程平台场景】
角色：课程发布平台的客服。
任务：告知机构客户，课程发布页面将新增"标准直播"和"低延迟直播"两个独立选项。当需要实时互动时，鼓励选择低延迟直播。
核心流程：
1. 身份确认（是否负责人）。
2. 确认是否知情（后台曾走低延迟线路）。
3. 传达升级内容：区别（标准：5-10秒延迟，便宜；低延迟：1-2秒，贵一点）和价格。
4. 询问发布方式（Web控制台/校务系统A/SaaS系统B），并引导开通（如果未显示）。
5. 检查学员端费用设置（如有）。
6. 添加企业微信。
7. 结束祝福。
约束：每次回复15-20字（不包含标点符号）；口语化；频繁给商家发言；被打断用过渡语；不说语气词；不能承诺优惠券
【宽容评估规则】
- **价格相关**：如果客服本身并不知道具体价格，所以如回复“价格因配置不同有差异，我短信发您”等类似话语，视为合理应对，不扣分。严禁因为客服未给出具体数字就判为策略灵活性低。
- **信息密度**：允许一句话包含多个合理信息（例如同时告知新增功能和确认知情），只要语义清晰、不违反核心事实，**不扣自然度分**。
- **字数限制**：15-20字允许±5字浮动（即10-25字），超出但意思完整的不作为严重违规。
- 紧急流程处理（仅适用于用户明确表达“忙”的轮次）：用户说“开会”、“在忙”、“有事”、“下次再说”或“没兴趣”等时，客服允许使用“就1分钟”等压缩话术，允许跳过第4，5，6步骤，但要在报告里说明。字数限制可放宽。只要成功让用户理解核心要求并结束，不因跳过子步骤而扣分。
- 开车情况处理：用户说“开车”时，客服必须说“那稍后再给您打，注意安全。”，立即结束对话，不再输出任何内容。不因跳过步骤而扣分。
- 当用户本身对升级有抵制时，评估不要太严苛，但仍保持专业的态度。

【对话记录】
{dialogue}

请按照以下JSON格式输出评估结果，要求评分基于实际表现，评语具体指出好/坏之处，并引用对话原文（引用时请写明第几轮）。
**重要：输出必须是合法的 JSON 对象，对象内每个键值对之间必须用逗号分隔，字符串内不能有未转义的双引号。不要输出任何其他文字。**
**重要：你必须输出 "readiness_score"（0-100之间的整数）和 "readiness_comment"（字符串，说明是否可以上线及风险点），这两个字段不可省略。**
{{
  "scores": {{
    "task_completion": 0-100,
    "process_adherence": 0-100,
    "naturalness": 0-100,
    "strategy_adaptation": 0-100
  }},
  "overall_score": 0-100,
  "strengths": ["优点1", "优点2"],
  "weaknesses": [
    {{
      "dimension": "naturalness",
      "turn": 2,
      "quote": "机器人原话",
      "reason": "为什么不好",
      "suggestion": "可以怎么说"
    }}
  ],
  "critical_incidents": [
    {{
      "turn": 3,
      "type": "用户拒绝",
      "robot_response": "...",
      "evaluation": "处理得当/不当，因为..."
    }}
  ],
  "improvement_suggestions": [
    "针对系统提示词的建议1",
    "针对模型训练的建议2"
  ],
  "readiness_score": 0-100,
  "readiness_comment": "说明是否可以上线及风险点"
}}
"""

class DeepEvaluator:
    def __init__(self, scenario: str):
        self.scenario = scenario
        self.llm = LLMClient()

    def _format_dialogue(self, dialogue_history: List[Dict]) -> str:
        lines = []
        for i, turn in enumerate(dialogue_history, 1):
            model = turn.get('model', '')
            user = turn.get('user', '')
            lines.append(f"第{i}轮 机器人：{model}")
            lines.append(f"第{i}轮 用户：{user}")
        return "\n".join(lines)

    def _normalize_turns(self, obj):
        if isinstance(obj, dict):
            new_obj = {}
            for k, v in obj.items():
                if k == 'turn' and isinstance(v, int):
                    new_obj[k] = str(v)
                else:
                    new_obj[k] = self._normalize_turns(v)
            return new_obj
        elif isinstance(obj, list):
            return [self._normalize_turns(item) for item in obj]
        else:
            return obj

    def _clean_json(self, raw: str) -> str:
        """尝试修复常见的 JSON 格式错误"""
        # 去除 markdown 代码块标记
        raw = re.sub(r'```json\s*', '', raw)
        raw = re.sub(r'```\s*$', '', raw)
        # 移除注释 (// 和 /* */)
        raw = re.sub(r'//.*?\n', '', raw)
        raw = re.sub(r'/\*.*?\*/', '', raw, flags=re.DOTALL)
        # 去除尾随逗号
        raw = re.sub(r',\s*}', '}', raw)
        raw = re.sub(r',\s*]', ']', raw)
        # 简单修复字符串内未转义的双引号（不完美，但尝试）
        # 为了安全，不自动转义，因为这可能破坏语义。
        return raw.strip()

    def evaluate(self, dialogue_history: List[Dict]) -> Dict:
        dialogue_text = self._format_dialogue(dialogue_history)
        if self.scenario == "delivery":
            prompt = DEEP_EVALUATION_PROMPT_DELIVERY.replace("{dialogue}", dialogue_text)
        elif self.scenario == "course":
            prompt = DEEP_EVALUATION_PROMPT_COURSE.replace("{dialogue}", dialogue_text)
        else:
            raise ValueError(f"Unknown scenario: {self.scenario}")

        try:
            response = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.2)

            # 新增：打印原始响应的最后 500 字符（查看是否包含 readiness_score）
            logger.info(f"Response tail (last 500 chars): {response[-500:]}")

            # 提取 JSON 字符串
            json_str = None
            # 1. 尝试匹配 markdown 代码块
            match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                # 2. 查找第一个 { 和最后一个 }
                start = response.find('{')
                end = response.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str = response[start:end+1]
            if not json_str:
                raise ValueError("No JSON found in response")

            # 清理 JSON 字符串
            json_str = self._clean_json(json_str)
            # 尝试解析
            result = json_repair.loads(json_str)
            result = self._normalize_turns(result)

            # 补全默认值
            result.setdefault("scores", {})
            for k in ["task_completion", "process_adherence", "naturalness", "strategy_adaptation"]:
                result["scores"].setdefault(k, 0)
            result.setdefault("overall_score", 0)
            result.setdefault("strengths", [])
            result.setdefault("weaknesses", [])
            result.setdefault("critical_incidents", [])
            result.setdefault("improvement_suggestions", [])
            result.setdefault("readiness_score", 0)
            result.setdefault("readiness_comment", "")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            # 打印错误位置附近的原文片段
            if 'json_str' in locals():
                lines = json_str.splitlines()
                error_line = e.lineno - 1
                start_line = max(0, error_line - 2)
                end_line = min(len(lines), error_line + 3)
                context = "\n".join(lines[start_line:end_line])
                logger.error(f"Error near line {e.lineno}, column {e.colno}:\n{context}")
            # 返回默认值
            return {
                "scores": {k: 0 for k in ["task_completion", "process_adherence", "naturalness", "strategy_adaptation"]},
                "overall_score": 0,
                "strengths": [],
                "weaknesses": [{"dimension": "error", "turn": "0", "quote": "", "reason": f"JSON解析失败: {e}", "suggestion": "检查模型输出"}],
                "critical_incidents": [],
                "improvement_suggestions": [],
                "readiness_score": 0,
                "readiness_comment": "评估出错，无法判断"
            }
        except Exception as e:
            logger.error(f"Deep evaluation failed: {e}")
            if 'response' in locals():
                logger.error(f"Response preview: {response[:500]}")
            return {
                "scores": {k: 0 for k in ["task_completion", "process_adherence", "naturalness", "strategy_adaptation"]},
                "overall_score": 0,
                "strengths": [],
                "weaknesses": [{"dimension": "error", "turn": "0", "quote": "", "reason": f"评估失败: {e}", "suggestion": "检查API和日志"}],
                "critical_incidents": [],
                "improvement_suggestions": [],
                "readiness_score": 0,
                "readiness_comment": "评估出错，无法判断"
            }