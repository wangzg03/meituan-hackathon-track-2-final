# evaluator/functional_validator.py
from typing import List, Dict

class FunctionalValidator:
    @staticmethod
    def validate(dialogue_history: List[Dict], required_steps: List[str]) -> Dict:
        full_text = " ".join([turn.get("model", "") for turn in dialogue_history])

        step_keywords = {
            "告知合同生效": ["合同生效", "已生效", "合同今天生效", "签署合同", "飞毛腿合同"],
            "询问是否可以配送": ["可以配送", "开始配送", "正常配送", "能跑吗", "方便配送", "能不能跑"],
            "说明不同合同配送要求": ["当天", "当日", "生效当天", "单日", "多日", "单日合同", "多日合同", "连续", "天", "每天", "需要连续", "连续Y天", "连续几天"],
            "挽留或鼓励": ["挽留", "鼓励", "理解", "试试", "注意安全", "不妨试试"],
            "提醒安全": ["安全", "注意安全", "路上小心"],
            "确认负责人身份": ["负责人", "校区负责人", "机构负责人"],
            "确认是否知情低延迟线路": ["低延迟", "低延迟直播", "低延迟线路", "注意到", "清楚吗", "知道吗", "是否知情", "开通试用"],
            "解释标准与低延迟区别及价格": ["标准直播", "低延迟直播", "延迟", "费用", "价格", "便宜", "贵"],
            "询问发布方式并引导": ["Web控制台", "校务系统", "SaaS", "发课", "发布课程", "系统"],
            "检查学员端费用": ["学员端费用", "收费规则", "学员收费"],
            "企业微信添加": ["企业微信", "添加微信", "加微信"],
            "结束祝福": ["再见", "祝您", "顺利", "招生"]
        }

        step_results = {}
        passed_steps = []
        failed_steps = []

        for step in required_steps:
            keywords = step_keywords.get(step, step.split())
            matched = any(kw in full_text for kw in keywords if len(kw) > 1)
            evidence = ""
            if matched:
                for kw in keywords:
                    if kw in full_text and len(kw) > 1:
                        idx = full_text.find(kw)
                        start = max(0, idx - 20)
                        end = min(len(full_text), idx + 20)
                        evidence = f"...{full_text[start:end]}..."
                        break
            step_results[step] = {"passed": matched, "evidence": evidence}
            if matched:
                passed_steps.append(step)
            else:
                failed_steps.append(step)

        completion_rate = len(passed_steps) / len(required_steps) if required_steps else 1.0
        return {
            "passed_steps": passed_steps,
            "failed_steps": failed_steps,
            "step_details": step_results,
            "overall_functional_score": completion_rate,
            "completion_rate": completion_rate
        }

    @staticmethod
    def validate_with_llm(dialogue_history: List[Dict], required_steps: List[str], llm_client=None) -> Dict:
        dialogue_text = "\n".join([
            f"轮{i+1} 客服：{turn.get('model', '')}\n用户：{turn.get('user', '')}"
            for i, turn in enumerate(dialogue_history)
        ])
        prompt = f"""请分析以下对话，判断客服是否完成了以下必要的业务流程步骤。

对话记录：
{dialogue_text}

需要检查的步骤：
{chr(10).join(f'- {step}' for step in required_steps)}

对于每个步骤，判断是否已经完成。只输出 JSON 格式，不要有其他内容：
{{
    "step_results": {{
        "步骤1": true/false,
        "步骤2": true/false
    }},
    "completion_rate": 0-1之间的浮点数,
    "explanation": "简要说明"
}}
"""
        if llm_client:
            try:
                import json, re
                response = llm_client.chat([{"role": "user", "content": prompt}])
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return {
                        "passed_steps": [s for s, p in result.get("step_results", {}).items() if p],
                        "failed_steps": [s for s, p in result.get("step_results", {}).items() if not p],
                        "step_details": result.get("step_results", {}),
                        "overall_functional_score": result.get("completion_rate", 0),
                        "completion_rate": result.get("completion_rate", 0),
                        "llm_explanation": result.get("explanation", "")
                    }
            except:
                pass
        return FunctionalValidator.validate(dialogue_history, required_steps)