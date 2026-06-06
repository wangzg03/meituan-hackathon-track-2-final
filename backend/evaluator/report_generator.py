import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, output_dir="outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, scenario_name: str, dialogue_logs: Any,
                 aggregated_scores: Dict, final_score: float,
                 explanations: Dict[str, str],
                 violations: List[str],
                 naturalness_result: Dict = None) -> tuple[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if isinstance(dialogue_logs, list) and len(dialogue_logs) > 0 and isinstance(dialogue_logs[0], list):
            display_logs = dialogue_logs[0]
        else:
            display_logs = dialogue_logs if isinstance(dialogue_logs, list) else []
        report = {
            "scenario": scenario_name,
            "timestamp": timestamp,
            "evaluation_rounds": len(dialogue_logs) if isinstance(dialogue_logs, list) else 1,
            "final_score": final_score,
            "aggregated_scores": aggregated_scores,
            "explanations": explanations,
            "violations": violations,
            "dialogue_logs": display_logs
        }
        if naturalness_result:
            report["naturalness"] = naturalness_result
        json_path = os.path.join(self.output_dir, f"{scenario_name}_{timestamp}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        md_path = os.path.join(self.output_dir, f"{scenario_name}_{timestamp}.md")
        md_content = self._to_markdown(report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        return json_path, md_path

    def _to_markdown(self, report: Dict) -> str:
        lines = []
        lines.append(f"# 评测报告：{report['scenario']}")
        lines.append(f"**时间戳**: {report['timestamp']}")
        lines.append(f"**评测轮数**: {report['evaluation_rounds']}")
        lines.append(f"**综合得分**: {report['final_score']:.2f}")
        lines.append("")
        lines.append("## 各指标得分")
        for metric, score in report['aggregated_scores'].items():
            lines.append(f"- **{metric}**: {score:.2f}")
        lines.append("")
        lines.append("## 可解释性说明")
        for metric, explanation in report['explanations'].items():
            lines.append(f"- **{metric}**: {explanation}")
        lines.append("")
        lines.append("## 约束违规详情")
        violations = report.get("violations", [])
        if violations:
            for v in violations:
                lines.append(f"- {v}")
        else:
            lines.append("无违规")
        lines.append("")
        if "naturalness" in report:
            lines.append("## 自然度评估（AI裁判）")
            nat = report["naturalness"]
            lines.append(f"**自然度得分**: {nat.get('naturalness_score', 0)}/100")
            issues = nat.get("issues", [])
            if issues:
                lines.append("**不自然问题**：")
                for issue in issues:
                    lines.append(f"- 第{issue.get('turn','?')}轮 [{issue.get('type','')}]：{issue.get('quote','')} → {issue.get('reason','')}")
            else:
                lines.append("未发现明显不自然问题")
            lines.append(f"**建议**: {nat.get('suggestion', '无')}")
            lines.append("")
        lines.append("## 对话日志")
        logs = report.get('dialogue_logs', [])
        if not logs:
            lines.append("无有效对话记录")
        else:
            for i, turn in enumerate(logs):
                if isinstance(turn, dict):
                    lines.append(f"### 第{i+1}轮")
                    lines.append(f"**模型**: {turn.get('model', '')}")
                    lines.append(f"**用户**: {turn.get('user', '')}")
                    lines.append("")
                else:
                    lines.append(f"### 第{i+1}轮 (数据格式异常)")
        return "\n".join(lines)

    def generate_deep_report(self, scenario_name: str, dialogue_logs: list, deep_result: dict) -> tuple[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        display_logs = dialogue_logs[0] if dialogue_logs and isinstance(dialogue_logs[0], list) else dialogue_logs
        report = {
            "scenario": scenario_name,
            "timestamp": timestamp,
            "evaluation_rounds": len(dialogue_logs),
            "deep_evaluation": deep_result,
            "dialogue_logs": display_logs
        }
        json_path = os.path.join(self.output_dir, f"{scenario_name}_{timestamp}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        md_path = os.path.join(self.output_dir, f"{scenario_name}_{timestamp}.md")
        md_content = self._deep_to_markdown(report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        return json_path, md_path

    def _deep_to_markdown(self, report: dict) -> str:
        deep = report["deep_evaluation"]
        scores = deep.get("scores", {})
        lines = []
        lines.append(f"# 深度评测报告：{report['scenario']}")
        lines.append(f"**时间戳**: {report['timestamp']}")
        lines.append(f"**评测轮数**: {report['evaluation_rounds']}")
        lines.append(f"**综合得分**: {deep.get('overall_score', 0):.1f}/100")
        lines.append(f"**上线就绪度**: {deep.get('readiness_score', 0):.1f}/100")
        lines.append(f"**就绪度说明**: {deep.get('readiness_comment', '无')}")
        lines.append("")
        lines.append("## 各维度得分")
        for dim, score in scores.items():
            dim_name = {
                "task_completion": "任务达成度",
                "process_adherence": "流程完整性",
                "constraint_compliance": "约束遵循度",
                "naturalness": "沟通自然度",
                "strategy_adaptation": "策略灵活性"
            }.get(dim, dim)
            lines.append(f"- **{dim_name}**: {score:.1f}/100")
        lines.append("")

        # 新增：功能步骤完成情况展示
        lines.append("## 功能步骤完成情况")
        func_val = deep.get("functional_validation", {})
        if func_val:
            per_round = func_val.get("per_round", [])
            for idx, round_res in enumerate(per_round):
                lines.append(f"### 第{idx+1}轮")
                passed = round_res.get('passed_steps', [])
                failed = round_res.get('failed_steps', [])
                lines.append(f"- **通过的步骤**: {', '.join(passed) if passed else '无'}")
                lines.append(f"- **未通过的步骤**: {', '.join(failed) if failed else '无'}")
                lines.append("")
        else:
            lines.append("无功能验证数据")
            lines.append("")

        lines.append("## 优势亮点")
        for s in deep.get("strengths", []):
            lines.append(f"- {s}")
        if not deep.get("strengths"):
            lines.append("无明显优势")
        lines.append("")
        lines.append("## 问题与改进建议")
        for w in deep.get("weaknesses", []):
            lines.append(f"### 维度：{w.get('dimension', 'unknown')}")
            lines.append(f"- **问题语句**: \"{w.get('quote', '')}\"")
            lines.append(f"- **原因**: {w.get('reason', '')}")
            lines.append(f"- **改进建议**: {w.get('suggestion', '')}")
            lines.append("")
        lines.append("## 关键事件分析")
        for inc in deep.get("critical_incidents", []):
            lines.append(f"### 第{inc.get('turn', '?')}轮 - {inc.get('type', '事件')}")
            lines.append(f"- **机器人回复**: {inc.get('robot_response', '')}")
            lines.append(f"- **评估**: {inc.get('evaluation', '')}")
            lines.append("")
        lines.append("## 系统优化建议")
        for sug in deep.get("improvement_suggestions", []):
            lines.append(f"- {sug}")
        lines.append("")
        lines.append("## 对话日志")
        logs = report.get("dialogue_logs", [])
        for i, turn in enumerate(logs, 1):
            if isinstance(turn, dict):
                lines.append(f"### 第{i}轮")
                lines.append(f"**机器人**: {turn.get('model', '')}")
                lines.append(f"**用户**: {turn.get('user', '')}")
                lines.append("")
        return "\n".join(lines)