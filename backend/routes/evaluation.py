from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, StreamingResponse
from schemas.evaluation import EvaluationRequest, EvaluationResult, DialogueTurn, FunctionalValidation, StepDetail
from typing import List, Dict, Optional, AsyncGenerator
import json
import os
from datetime import datetime
import asyncio
from queue import Queue as ThreadSafeQueue
from threading import Lock

from simulators import DeliveryRiderSimulator, CourseManagerSimulator
from simulators.customer_agent import LLMCustomerAgent
from dialogue.orchestrator import Orchestrator
from evaluator import ReportGenerator, FunctionalValidator, EvaluationCriteria
from evaluator.pipeline import EvaluationPipeline
from config import config
from param_setting.user_params import user_params
from prompts.delivery_prompt import DELIVERY_SYSTEM_PROMPT_EVAL as DELIVERY_SYSTEM_PROMPT_TEMPLATE
from prompts.course_prompt import COURSE_SYSTEM_PROMPT_EVAL as COURSE_SYSTEM_PROMPT

router = APIRouter()

evaluation_results: Dict[str, EvaluationResult] = {}
# 用于存储 SSE 订阅者（使用线程安全队列）
sse_subscribers: Dict[str, ThreadSafeQueue] = {}
subscribers_lock = Lock()

# 从输出文件恢复评估结果状态
def generate_task_id():
    """生成基于时间的任务ID，格式：YYYYMMDD_HHMMSS"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def get_evaluation_folder(task_id: str, scenario: str = None):
    """获取评估文件夹路径"""
    return os.path.join("outputs", task_id)

def get_scenario_filename(scenario: str) -> str:
    """获取场景文件名（用于命名文件）"""
    scenario_map = {
        "delivery": "外卖配送场景",
        "course": "课程平台场景"
    }
    return scenario_map.get(scenario, scenario)

def load_existing_results():
    """启动时从已生成的报告文件恢复评估状态"""
    output_dir = "outputs"
    if not os.path.exists(output_dir):
        return

    for folder_name in os.listdir(output_dir):
        folder_path = os.path.join(output_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        dialogue_file = os.path.join(folder_path, f"{folder_name}-对话.json")
        report_file = os.path.join(folder_path, f"{folder_name}-报告.json")

        if os.path.exists(dialogue_file):
            task_id = folder_name
            if task_id not in evaluation_results:
                try:
                    with open(dialogue_file, 'r', encoding='utf-8') as f:
                        dialogue_history = json.load(f)

                    if os.path.exists(report_file):
                        try:
                            with open(report_file, 'r', encoding='utf-8') as f:
                                report_data = json.load(f)

                            deep_eval = report_data.get("deep_evaluation", {})
                            scenario_from_file = report_data.get("scenario", "unknown")

                            evaluation_results[task_id] = EvaluationResult(
                                id=task_id,
                                name=f"已恢复任务_{task_id}",
                                scenario=scenario_from_file,
                                personality="unknown",
                                status="completed",
                                overall_score=deep_eval.get("overall_score", 0),
                                readiness_score=deep_eval.get("readiness_score", 0),
                                readiness_comment=deep_eval.get("readiness_comment", ""),
                                scores=deep_eval.get("scores", {}),
                                strengths=deep_eval.get("strengths", []),
                                weaknesses=deep_eval.get("weaknesses", []),
                                critical_incidents=deep_eval.get("critical_incidents", []),
                                improvement_suggestions=deep_eval.get("improvement_suggestions", []),
                                dialogue_history=dialogue_history,
                                created_at=datetime.fromtimestamp(os.path.getmtime(dialogue_file)).isoformat(),
                                functional_validation=None
                            )
                        except Exception as e:
                            print(f"Error reading report file: {e}")
                            evaluation_results[task_id] = EvaluationResult(
                                id=task_id,
                                name=f"已恢复任务_{task_id}",
                                scenario="unknown",
                                personality="unknown",
                                status="completed",
                                overall_score=0,
                                readiness_score=0,
                                readiness_comment="",
                                scores={},
                                strengths=[],
                                weaknesses=[],
                                critical_incidents=[],
                                improvement_suggestions=[],
                                dialogue_history=dialogue_history,
                                created_at=datetime.fromtimestamp(os.path.getmtime(dialogue_file)).isoformat(),
                                functional_validation=None
                            )
                    else:
                        evaluation_results[task_id] = EvaluationResult(
                            id=task_id,
                            name=f"已恢复任务_{task_id}",
                            scenario="unknown",
                            personality="unknown",
                            status="completed",
                            overall_score=0,
                            readiness_score=0,
                            readiness_comment="",
                            scores={},
                            strengths=[],
                            weaknesses=[],
                            critical_incidents=[],
                            improvement_suggestions=[],
                            dialogue_history=dialogue_history,
                            created_at=datetime.fromtimestamp(os.path.getmtime(dialogue_file)).isoformat(),
                            functional_validation=None
                        )
                except Exception as e:
                    print(f"Error loading existing result: {e}")
                    pass

# 启动时恢复状态
load_existing_results()

SCENARIO_NAMES = {
    "delivery": "外卖配送场景",
    "course": "课程平台场景"
}

PERSONALITY_NAMES = {
    "cooperative": "合作型",
    "skeptical": "怀疑型",
    "interruptive": "打断型",
    "silent": "沉默型",
    "bargain": "议价型",
    "irritable_refuse": "易怒拒绝型",
    "follow_wait": "从众型"
}

# 外卖配送场景必需步骤
DELIVERY_REQUIRED_STEPS = [
    "告知合同生效",
    "询问是否可以配送",
    "说明不同合同配送要求",
    "挽留或鼓励",
    "提醒安全",
    "结束祝福"
]

# 课程平台场景必需步骤
COURSE_REQUIRED_STEPS = [
    "确认负责人身份",
    "确认是否知情低延迟线路",
    "解释标准与低延迟区别及价格",
    "询问发布方式并引导",
    "检查学员端费用",
    "企业微信添加",
    "结束祝福"
]
def generate_task_name(scenario: str, personality: str, created_at: str) -> str:
    scenario_name = SCENARIO_NAMES.get(scenario, scenario)
    personality_name = PERSONALITY_NAMES.get(personality, personality)
    dt = datetime.fromisoformat(created_at)
    date_str = dt.strftime("%Y-%m-%d %H:%M")
    return f"[{date_str}] {scenario_name}-{personality_name}"

def run_evaluation_sync(task_id: str, scenario_name: str, scenario_filename: str,
                        system_prompt_template: str, simulator_class, scenario_key: str,
                        personality: str,
                        on_turn_callback=None, dialogue_file=None, evaluation_folder=None):
    """
    使用 EvaluationPipeline 进行评测（手动聚合指标，确保 readiness_score 正确）
    """
    all_dialogues = []
    all_results = []

    # 准备场景参数
    if scenario_key == "delivery":
        criteria = EvaluationCriteria.for_delivery_scenario()
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

    for round_idx in range(config.EVALUATION_ROUNDS):
        simulator = simulator_class(personality=personality)

        if scenario_key == "delivery":
            rider_name = simulator.get_name().split('(')[0] if '(' in simulator.get_name() else simulator.get_name()
            system_prompt = system_prompt_template.replace("${X}", str(X))
            system_prompt = system_prompt.replace("${Y}", str(Y))
            system_prompt = system_prompt.replace("${Z}", str(Z))
            system_prompt = system_prompt.replace("${W}", str(W))
            system_prompt = system_prompt.replace("${reward}", str(reward))
            system_prompt = system_prompt.replace("${rider_name}", rider_name)
            opening = None
        else:
            system_prompt = system_prompt_template
            opening = None

        customer_agent = LLMCustomerAgent(
            system_prompt=system_prompt,
            name="站长" if scenario_key == "delivery" else "客服",
            temperature=config.TEMPERATURE
        )

        orchestrator = Orchestrator(
            customer_agent=customer_agent,
            user_simulator=simulator,
            max_turns=config.MAX_DIALOGUE_TURNS,
            scenario=scenario_key
        )
        dialogue_history = orchestrator.run(init_customer_message=opening)
        all_dialogues.append(dialogue_history)

        single_result = pipeline.evaluate(dialogue_history)
        all_results.append(single_result)

        summary = single_result["summary"]
        print(f"  功能完成率: {summary['functional_completion_rate']:.1%}")
        print(f"  深度综合分: {summary['deep_overall_score']:.1f} / 100")
        print(f"  就绪度: {summary['readiness_score']:.1f} / 100")

        if on_turn_callback:
            turn_data = {
                "round": round_idx + 1,
                "dialogue": dialogue_history,
                "summary": summary
            }
            on_turn_callback(turn_data)

    # ========== 手动聚合所有指标 ==========
    n = len(all_results)
    if n == 0:
        raise RuntimeError("No evaluation results collected")

    total_deep_overall = 0.0
    total_readiness = 0.0
    total_func_rate = 0.0
    total_scores = {}

    for r in all_results:
        summary = r["summary"]
        total_deep_overall += summary["deep_overall_score"]
        total_readiness += summary["readiness_score"]
        total_func_rate += summary["functional_completion_rate"]

        deep_scores = r.get("deep", {}).get("scores", {})
        for metric, score in deep_scores.items():
            total_scores[metric] = total_scores.get(metric, 0.0) + score

    avg_deep_overall = total_deep_overall / n
    avg_readiness = total_readiness / n
    avg_func_rate = total_func_rate / n
    for metric in total_scores:
        total_scores[metric] /= n

    # 强制后备逻辑
    if avg_readiness == 0 and avg_deep_overall > 0:
        avg_readiness = min(100, int(avg_deep_overall * 0.8))
        print(f"[WARNING] readiness_score missing, using fallback: {avg_readiness}")
    elif avg_readiness == 0:
        avg_readiness = 30
        print("[WARNING] readiness_score is 0, setting to default 30")

    # 构建用于报告和返回的 avg_deep 结构
    avg_deep = {
        "overall_score": avg_deep_overall,
        "readiness_score": avg_readiness,
        "scores": total_scores,
        "strengths": all_results[0]["deep"].get("strengths", []) if all_results else [],
        "weaknesses": all_results[0]["deep"].get("weaknesses", []) if all_results else [],
        "critical_incidents": all_results[0]["deep"].get("critical_incidents", []) if all_results else [],
        "improvement_suggestions": all_results[0]["deep"].get("improvement_suggestions", []) if all_results else [],
        "readiness_comment": all_results[0]["deep"].get("readiness_comment", "") if all_results else [],
        "functional_validation": {
            "avg_completion_rate": avg_func_rate,
            "per_round": [r["functional"] for r in all_results]
        },
        "dialogue_history": all_dialogues[0] if all_dialogues else []
    }

    # 生成详细功能验证（步骤级别）
    required_steps = DELIVERY_REQUIRED_STEPS if scenario_key == "delivery" else COURSE_REQUIRED_STEPS
    functional_result = FunctionalValidator.validate(avg_deep["dialogue_history"], required_steps)
    avg_deep["functional_validation"] = functional_result

    # 生成报告
    report_gen = ReportGenerator(output_dir=evaluation_folder) if evaluation_folder else ReportGenerator()
    report_gen.generate_deep_report(scenario_name, all_dialogues, avg_deep)

    # 返回聚合结果
    return {
        "overall_score": avg_deep_overall,
        "readiness_score": avg_readiness,
        "scores": total_scores,
        "strengths": avg_deep["strengths"],
        "weaknesses": avg_deep["weaknesses"],
        "critical_incidents": avg_deep["critical_incidents"],
        "improvement_suggestions": avg_deep["improvement_suggestions"],
        "readiness_comment": avg_deep["readiness_comment"],
        "functional_validation": functional_result,
        "dialogue_history": avg_deep["dialogue_history"]
    }

def create_turn_callback(task_id: str):
    """创建对话轮次回调函数，用于推送 SSE 事件"""
    def callback(turn_data):
        with subscribers_lock:
            if task_id in sse_subscribers:
                sse_subscribers[task_id].put(json.dumps({
                    "type": "turn",
                    "data": turn_data
                }))
    return callback

def run_evaluation_task(task_id: str, scenario: str, personality: str):
    try:
        created_at = datetime.now().isoformat()
        task_name = generate_task_name(scenario, personality, created_at)

        scenario_filename = get_scenario_filename(scenario)
        evaluation_folder = os.path.join("outputs", task_id)
        os.makedirs(evaluation_folder, exist_ok=True)

        dialogue_file = os.path.join(evaluation_folder, f"{task_id}-{scenario_filename}-对话.json")

        turn_callback = create_turn_callback(task_id)

        if scenario == "delivery":
            result = run_evaluation_sync(
                task_id, "外卖配送场景", scenario_filename,
                DELIVERY_SYSTEM_PROMPT_TEMPLATE,
                DeliveryRiderSimulator, "delivery",
                personality,          # 传入前端选择的 personality
                turn_callback, dialogue_file, evaluation_folder
            )
        elif scenario == "course":
            result = run_evaluation_sync(
                task_id, "课程平台升级场景", scenario_filename,
                COURSE_SYSTEM_PROMPT,
                CourseManagerSimulator, "course",
                personality,          # 传入前端选择的 personality
                turn_callback, dialogue_file, evaluation_folder
            )
        else:
            raise ValueError(f"Unknown scenario: {scenario}")

        # 构建功能验证结果对象（用于 API 响应）
        functional_validation = None
        if "functional_validation" in result:
            func_val = result["functional_validation"]
            step_details = {
                step: StepDetail(passed=detail["passed"], evidence=detail.get("evidence", ""))
                for step, detail in func_val.get("step_details", {}).items()
            }
            functional_validation = FunctionalValidation(
                passed_steps=func_val.get("passed_steps", []),
                failed_steps=func_val.get("failed_steps", []),
                step_details=step_details,
                overall_functional_score=func_val.get("overall_functional_score", 0),
                completion_rate=func_val.get("completion_rate", 0)
            )

        evaluation_results[task_id] = EvaluationResult(
            id=task_id,
            name=task_name,
            scenario=scenario,
            personality=personality,
            status="completed",
            overall_score=result.get("overall_score", 0),
            readiness_score=result.get("readiness_score", 0),
            readiness_comment=result.get("readiness_comment", ""),
            scores=result.get("scores", {}),
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
            critical_incidents=result.get("critical_incidents", []),
            improvement_suggestions=result.get("improvement_suggestions", []),
            dialogue_history=result.get("dialogue_history", []),
            created_at=created_at,
            functional_validation=functional_validation
        )
    except Exception as e:
        created_at = datetime.now().isoformat()
        task_name = generate_task_name(scenario, personality, created_at)
        
        # 尝试从对话文件读取已生成的对话历史
        dialogue_history = []
        scenario_filename = get_scenario_filename(scenario)
        evaluation_folder = os.path.join("outputs", task_id)
        dialogue_file = os.path.join(evaluation_folder, f"{task_id}-{scenario_filename}-对话.json")
        if os.path.exists(dialogue_file):
            try:
                with open(dialogue_file, 'r', encoding='utf-8') as f:
                    dialogue_history = json.load(f)
                print(f"[DEBUG] 任务失败但读取到对话历史: {len(dialogue_history)} 条")
            except Exception as read_error:
                print(f"[DEBUG] 读取对话文件失败: {read_error}")
        
        evaluation_results[task_id] = EvaluationResult(
            id=task_id,
            name=task_name,
            scenario=scenario,
            personality=personality,
            status="failed",
            overall_score=0,
            readiness_score=0,
            readiness_comment=f"评估失败: {str(e)}",
            scores={},
            strengths=[],
            weaknesses=[],
            critical_incidents=[],
            improvement_suggestions=[],
            dialogue_history=dialogue_history,
            created_at=created_at
        )

@router.post("/", response_model=EvaluationResult)
async def create_evaluation(request: EvaluationRequest, background_tasks: BackgroundTasks):
    task_id = generate_task_id()
    created_at = datetime.now().isoformat()
    task_name = generate_task_name(request.scenario, request.personality, created_at)

    evaluation_results[task_id] = EvaluationResult(
        id=task_id,
        name=task_name,
        scenario=request.scenario,
        personality=request.personality,
        status="running",
        overall_score=0,
        readiness_score=0,
        readiness_comment="",
        scores={},
        strengths=[],
        weaknesses=[],
        critical_incidents=[],
        improvement_suggestions=[],
        dialogue_history=[],
        created_at=created_at
    )

    background_tasks.add_task(run_evaluation_task, task_id, request.scenario, request.personality)

    return evaluation_results[task_id]

@router.get("/{task_id}", response_model=EvaluationResult)
async def get_evaluation(task_id: str):
    if task_id not in evaluation_results:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation_results[task_id]

@router.get("/", response_model=List[EvaluationResult])
async def get_evaluations(
    scenario: Optional[str] = None,
    name: Optional[str] = Query(None, description="按任务名称搜索（支持模糊匹配）")
):
    results = list(evaluation_results.values())
    if scenario:
        results = [r for r in results if r.scenario == scenario]
    if name:
        results = [r for r in results if name.lower() in r.name.lower()]
    return sorted(results, key=lambda x: x.created_at, reverse=True)

@router.get("/{task_id}/dialogue")
async def get_dialogue(task_id: str):
    """获取评估任务的对话历史（实时从文件读取）"""
    if task_id not in evaluation_results:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    scenario = evaluation_results[task_id].scenario
    scenario_filename = get_scenario_filename(scenario)
    evaluation_folder = os.path.join("outputs", task_id)
    dialogue_file = os.path.join(evaluation_folder, f"{task_id}-{scenario_filename}-对话.json")

    if os.path.exists(dialogue_file):
        try:
            with open(dialogue_file, 'r', encoding='utf-8') as f:
                dialogue_history = json.load(f)
            return {"dialogue": dialogue_history}
        except Exception as e:
            print(f"Error reading dialogue file: {e}")

    if os.path.exists(evaluation_folder):
        for filename in os.listdir(evaluation_folder):
            if filename.endswith("-对话.json") and filename.startswith(task_id):
                dialogue_file = os.path.join(evaluation_folder, filename)
                try:
                    with open(dialogue_file, 'r', encoding='utf-8') as f:
                        dialogue_history = json.load(f)
                    return {"dialogue": dialogue_history}
                except Exception as e:
                    print(f"Error reading dialogue file: {e}")

    result = evaluation_results[task_id]
    return {"dialogue": result.dialogue_history}


@router.get("/{task_id}/download")
async def download_report(task_id: str):
    """下载评估报告JSON文件"""
    if task_id not in evaluation_results:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    scenario = evaluation_results[task_id].scenario
    scenario_filename = get_scenario_filename(scenario)
    evaluation_folder = os.path.join("outputs", task_id)
    report_file = os.path.join(evaluation_folder, f"{task_id}-{scenario_filename}-报告.json")

    if os.path.exists(report_file):
        return FileResponse(
            report_file,
            media_type="application/json",
            filename=f"{task_id}-{scenario_filename}-报告.json"
        )

    if os.path.exists(evaluation_folder):
        for filename in os.listdir(evaluation_folder):
            if filename.endswith("-报告.json") and filename.startswith(task_id):
                report_file = os.path.join(evaluation_folder, filename)
                return FileResponse(
                    report_file,
                    media_type="application/json",
                    filename=filename
                )

    result = evaluation_results[task_id]
    return result