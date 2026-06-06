# evaluator/evaluator.py
from .metrics import MetricsCalculator
from .deep_evaluator import DeepEvaluator
from .functional_validator import FunctionalValidator
from .report_generator import ReportGenerator
from typing import List, Dict

class Evaluator:
    def __init__(self, scenario: str, criteria):
        self.scenario = scenario
        self.criteria = criteria
        self.metrics_calc = MetricsCalculator()
        self.functional_validator = FunctionalValidator()
        self.deep_evaluator = DeepEvaluator(scenario)
        self.reporter = ReportGenerator()

    def evaluate_single(self, dialogue_history: List[Dict]) -> Dict:
        # 客观约束
        constraint_score, violations = self.metrics_calc.compute_constraint_score(dialogue_history, self.scenario)
        # 功能验证
        functional_result = self.functional_validator.validate(dialogue_history, self.criteria.required_steps)
        # 深度评估
        deep_result = self.deep_evaluator.evaluate(dialogue_history)
        # 覆盖
        if "scores" in deep_result:
            deep_result["scores"]["constraint_compliance"] = constraint_score * 100
        else:
            deep_result["scores"] = {"constraint_compliance": constraint_score * 100}
        deep_result["constraint_violations"] = violations
        deep_result["functional_validation"] = functional_result
        return {
            "functional_validation": functional_result,
            "deep_evaluation": deep_result
        }

    def evaluate_and_report(self, dialogue_history: List[Dict], round_index: int = 0) -> tuple[str, str]:
        result = self.evaluate_single(dialogue_history)
        deep_result = result["deep_evaluation"]
        json_path, md_path = self.reporter.generate_deep_report(
            f"{self.criteria.name}_round{round_index}",
            [dialogue_history],
            deep_result
        )
        return json_path, md_path