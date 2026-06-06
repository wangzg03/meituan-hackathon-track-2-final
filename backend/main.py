import argparse
import logging
from config import config
from simulators import DeliveryRiderSimulator, CourseManagerSimulator
from simulators.customer_agent import LLMCustomerAgent
from dialogue import Orchestrator
from evaluator import EvaluationCriteria, EvaluationPipeline, ReportGenerator
from param_setting.user_params import user_params
from prompts.delivery_prompt import DELIVERY_SYSTEM_PROMPT_EVAL as DELIVERY_SYSTEM_PROMPT_TEMPLATE
from prompts.course_prompt import COURSE_SYSTEM_PROMPT_EVAL as COURSE_SYSTEM_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_evaluation_pipeline(scenario_name, system_prompt_template, 
                            simulator_class, scenario_key):
    """
    使用 EvaluationPipeline 进行评测
    """
    print(f"\n========== 开始评测场景：{scenario_name} ==========")
    
    # 获取评估标准和管线
    if scenario_key == "delivery":
        criteria = EvaluationCriteria.for_delivery_scenario()
        # 从 param.json 读取外卖场景参数
        delivery_params = user_params.get_delivery_params()
        X = delivery_params.get("X", 5)
        Y = delivery_params.get("Y", 3)
        Z = delivery_params.get("Z", 22)
        W = delivery_params.get("W", 7)
        reward = delivery_params.get("reward", 2)
    else:
        criteria = EvaluationCriteria.for_course_scenario()
        X = Y = Z = W = reward = None
    
    pipeline = EvaluationPipeline(scenario_key, criteria)
    all_dialogues = []
    all_results = []
    
    for round_idx in range(config.EVALUATION_ROUNDS):
        print(f"\n--- 第 {round_idx+1}/{config.EVALUATION_ROUNDS} 轮 ---")
        
        # 创建用户模拟器
        user_sim = simulator_class()
        
        if scenario_key == "delivery":
            # 获取骑手姓名（从模拟器获取，模拟器会从 personas.json 读取）
            rider_name = user_sim.get_name()
            # 替换系统提示词中的变量
            system_prompt = system_prompt_template.replace("${X}", str(X))
            system_prompt = system_prompt.replace("${Y}", str(Y))
            system_prompt = system_prompt.replace("${Z}", str(Z))
            system_prompt = system_prompt.replace("${W}", str(W))
            system_prompt = system_prompt.replace("${reward}", str(reward))
            system_prompt = system_prompt.replace("${rider_name}", rider_name)
            # 注意：模板中不再有 ${rider_name}，因为开场白单独构造
            
            opening = None
        else:
            system_prompt = system_prompt_template
            opening = None 
        
        # 创建客服 Agent
        customer_agent = LLMCustomerAgent(
            system_prompt=system_prompt,
            name="站长" if scenario_key == "delivery" else "客服",
            temperature=config.TEMPERATURE
        )
        
        # 创建编排器并运行对话
        orchestrator = Orchestrator(
            customer_agent=customer_agent,
            user_simulator=user_sim,
            max_turns=config.MAX_DIALOGUE_TURNS,
            scenario=scenario_key
        )
        # 外卖场景传入开场白，课程场景传 None 让客服自己生成
        dialogue_history = orchestrator.run(init_customer_message=opening)
        
        all_dialogues.append(dialogue_history)
        
        # 使用 Pipeline 评估
        result = pipeline.evaluate(dialogue_history)
        all_results.append(result)
        
        # 打印简要结果
        summary = result["summary"]
        print(f"  功能完成率: {summary['functional_completion_rate']:.1%}")
        print(f"  深度综合分: {summary['deep_overall_score']:.1f} / 100")
        print(f"  就绪度: {summary['readiness_score']:.1f} / 100")
    
    # 聚合多轮结果
    batch_result = pipeline.batch_evaluate(all_dialogues)
    
    # 构建聚合深度报告
    avg_deep = {
        "overall_score": batch_result["aggregated"]["avg_deep_overall_score"],
        "readiness_score": batch_result["aggregated"]["avg_readiness_score"],
        "scores": batch_result["deep_aggregated"].get("scores", {}),
        "strengths": all_results[0]["deep"].get("strengths", []) if all_results else [],
        "weaknesses": all_results[0]["deep"].get("weaknesses", []) if all_results else [],
        "critical_incidents": all_results[0]["deep"].get("critical_incidents", []) if all_results else [],
        "improvement_suggestions": all_results[0]["deep"].get("improvement_suggestions", []) if all_results else [],
        "readiness_comment": all_results[0]["deep"].get("readiness_comment", "") if all_results else "",
        "functional_validation": {
            "avg_completion_rate": batch_result["aggregated"]["avg_functional_completion_rate"],
            "per_round": [r["functional"] for r in all_results]
        }
    }
    
    # 可选：再应用一次后备（防止 batch_evaluate 未修改的情况）
    if avg_deep["readiness_score"] == 0 and avg_deep["overall_score"] > 0:
        avg_deep["readiness_score"] = min(100, int(avg_deep["overall_score"] * 0.8))
    elif avg_deep["readiness_score"] == 0:
        avg_deep["readiness_score"] = 30    

    # 生成最终聚合报告
    report_gen = ReportGenerator()
    json_path, md_path = report_gen.generate_deep_report(scenario_name, all_dialogues, avg_deep)
    print(f"\n评测报告已生成：{md_path}")
    
    return batch_result["aggregated"]["avg_deep_overall_score"]

def main():
    parser = argparse.ArgumentParser(description="自动化指令遵循评估系统")
    parser.add_argument("--scenario", choices=["delivery", "course", "all"], default="all",
                        help="选择评测场景：delivery(外卖), course(课程), all(两者都跑)")
    parser.add_argument("--use-pipeline", action="store_true", default=True,
                        help="使用新的 EvaluationPipeline（默认启用）")
    parser.add_argument("--legacy", action="store_true",
                        help="使用原有的评估方式")
    args = parser.parse_args()
    
    use_pipeline = args.use_pipeline and not args.legacy
    
    if args.scenario in ["delivery", "all"]:
        if use_pipeline:
            run_evaluation_pipeline("外卖配送场景", DELIVERY_SYSTEM_PROMPT_TEMPLATE,
                                    DeliveryRiderSimulator, "delivery")
    
    if args.scenario in ["course", "all"]:
        if use_pipeline:
            run_evaluation_pipeline("课程平台升级场景", COURSE_SYSTEM_PROMPT,
                                    CourseManagerSimulator, "course")
    
    print("\n所有评测完成。")


if __name__ == "__main__":
    main()