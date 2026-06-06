# evaluator/pipeline.py
"""
统一评估管线
- 功能正确性验证（Functional Validation）- 检查业务流程是否完成（内部参考）
- 客观约束遵守（MetricsCalculator）- 字数、重复、禁用词等硬性指标
- LLM-as-a-judge（深度评估）- 任务达成、流程完整、自然度、策略灵活性
"""

from typing import List, Dict, Optional
import logging
from .metrics import MetricsCalculator
from .functional_validator import FunctionalValidator
from .deep_evaluator import DeepEvaluator
from .report_generator import ReportGenerator
from dialogue.dialog import Dialog

logger = logging.getLogger(__name__)


class EvaluationPipeline:
    def __init__(self, scenario: str, criteria, llm_client=None):
        self.scenario = scenario
        self.criteria = criteria
        self.metrics_calc = MetricsCalculator()
        self.functional_validator = FunctionalValidator()
        self.deep_evaluator = DeepEvaluator(scenario)
        self.reporter = ReportGenerator()

    def evaluate(self, dialogue_history: List[Dict], dialog: Optional[Dialog] = None) -> Dict:
        # 1. 客观约束遵守（硬性指标）
        constraint_score, constraint_violations = self.metrics_calc.compute_constraint_score(dialogue_history, self.scenario)

        # 2. 功能正确性验证（仅供参考，不参与最终评分）
        functional_results = self.functional_validator.validate(
            dialogue_history,
            self.criteria.required_steps
        )

        # 3. 深度评估（LLM 评估语义和流程维度）
        deep_results = self.deep_evaluator.evaluate(dialogue_history)

        # 4. 覆盖约束遵守维度（用客观规则分替换 LLM 给出的分）
        if "scores" in deep_results:
            deep_results["scores"]["constraint_compliance"] = constraint_score * 100  # 转为0-100
        else:
            deep_results["scores"] = {"constraint_compliance": constraint_score * 100}
        deep_results["constraint_violations"] = constraint_violations

        return {
            "functional": functional_results,
            "deep": deep_results,
            "summary": {
                "functional_completion_rate": functional_results.get("completion_rate", 0),
                "deep_overall_score": deep_results.get("overall_score", 0),
                "readiness_score": deep_results.get("readiness_score", 0),
                "readiness_comment": deep_results.get("readiness_comment", "")
            }
        }

    def evaluate_dialog(self, dialog: Dialog) -> Dict:
        history = dialog.to_legacy_history()
        return self.evaluate(history)

    def generate_report(self, evaluation_result: Dict, scenario_name: str,
                        dialogue_history: List[Dict], round_index: int = 0) -> tuple[str, str]:
        deep_result = evaluation_result["deep"]
        deep_result["functional_validation"] = evaluation_result["functional"]
        json_path, md_path = self.reporter.generate_deep_report(
            f"{scenario_name}_round{round_index}",
            [dialogue_history],
            deep_result
        )
        return json_path, md_path

    def batch_evaluate(self, dialogue_list: List[List[Dict]]) -> Dict:
        all_results = []
        for dialogue_history in dialogue_list:
            result = self.evaluate(dialogue_history)
            all_results.append(result)

        n = len(all_results)
        if n == 0:
            return {}

        avg_deep_scores = {}
        deep_keys = ["overall_score", "readiness_score"]
        for key in deep_keys:
            values = [r["deep"].get(key, 0) for r in all_results]
            avg_deep_scores[key] = sum(values) / n

        # readiness_score 后备逻辑
        avg_readiness = avg_deep_scores.get("readiness_score", 0)
        avg_overall = avg_deep_scores.get("overall_score", 0)
        if avg_readiness == 0 and avg_overall > 0:
            avg_readiness = min(100, int(avg_overall * 0.8))
            print(f"[WARNING] batch_evaluate: readiness_score missing, using fallback: {avg_readiness}")
        elif avg_readiness == 0:
            avg_readiness = 30
            print("[WARNING] batch_evaluate: readiness_score is 0, setting to default 30")
        avg_deep_scores["readiness_score"] = avg_readiness

        # 深度评估的五维度平均（但约束遵循度已被规则覆盖，这里仍求平均）
        if all_results and "scores" in all_results[0]["deep"]:
            avg_scores = {}
            for metric in all_results[0]["deep"]["scores"].keys():
                values = [r["deep"]["scores"].get(metric, 0) for r in all_results]
                avg_scores[metric] = sum(values) / n
            avg_deep_scores["scores"] = avg_scores

        avg_functional = sum(r["functional"].get("completion_rate", 0) for r in all_results) / n

        return {
            "num_rounds": n,
            "aggregated": {
                "avg_functional_completion_rate": avg_functional,
                "avg_deep_overall_score": avg_deep_scores.get("overall_score", 0),
                "avg_readiness_score": avg_readiness
            },
            "deep_aggregated": avg_deep_scores,
            "individual_results": all_results
        }


class PipelineFactory:
    @staticmethod
    def for_delivery(criteria=None):
        from .criteria import EvaluationCriteria
        if criteria is None:
            criteria = EvaluationCriteria.for_delivery_scenario()
        return EvaluationPipeline("delivery", criteria)

    @staticmethod
    def for_course(criteria=None):
        from .criteria import EvaluationCriteria
        if criteria is None:
            criteria = EvaluationCriteria.for_course_scenario()
        return EvaluationPipeline("course", criteria)