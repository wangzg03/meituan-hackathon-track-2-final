from fastapi import APIRouter
from schemas.evaluation import ScenarioInfo, PersonalityInfo

router = APIRouter()

SCENARIOS = [
    {
        "key": "delivery",
        "name": "外卖配送场景",
        "description": "模拟美团外卖站长致电飞毛腿骑手沟通配送任务"
    },
    {
        "key": "course",
        "name": "课程平台场景",
        "description": "模拟课程发布平台客服通知机构客户直播功能升级"
    }
]

PERSONALITIES = [
    {"key": "cooperative", "name": "合作型"},
    {"key": "skeptical", "name": "怀疑型"},
    {"key": "interruptive", "name": "打断型"},
    {"key": "silent", "name": "沉默型"},
    {"key": "bargain", "name": "议价型"},
    {"key": "irritable_refuse", "name": "易怒拒绝型"},
    {"key": "follow_wait", "name": "从众型"},
]

@router.get("/", response_model=list[ScenarioInfo])
async def get_scenarios():
    return SCENARIOS

@router.get("/personalities", response_model=list[PersonalityInfo])
async def get_personalities():
    return PERSONALITIES