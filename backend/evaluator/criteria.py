from dataclasses import dataclass
from typing import List, Dict

@dataclass
class EvaluationCriteria:
    """评估标准定义，每个场景独立"""
    name: str
    criteria: Dict[str, float]  # 指标名称和权重
    required_steps: List[str]   # 必须完成的流程步骤
    constraints: List[str]       # 必须遵守的约束
    
    @staticmethod
    def for_delivery_scenario():
        return EvaluationCriteria(
            name="外卖骑手通知",
            criteria={
                "任务完成": 0.4,      # 是否成功让骑手接受或合理结束
                "流程遵循": 0.2,      # 是否按Call Flow顺序
                "FAQ覆盖": 0.15,      # 关键知识点是否提及
                "约束遵守": 0.15,     # 字数、语气、重复等约束
                "挽留效果": 0.1       # 对不想配送骑手的挽留尝试
            },
            required_steps=[
                "告知合同生效",
                "询问是否可以配送",
                "说明连续Y天要求",
                "挽留或鼓励",
                "提醒安全"
            ],
            constraints=[
                "每条回复约30字以内",
                "避免重复",
                "超出职责时回复确认后回电",
                "坚持不配送则安慰后挂断"
            ]
        )
    
    @staticmethod
    def for_course_scenario():
        return EvaluationCriteria(
            name="课程平台升级通知",
            criteria={
                "身份确认": 0.1,
                "知情确认": 0.1,
                "区别与价格说明": 0.2,
                "发布方式引导": 0.2,
                "费用检查": 0.1,
                "企业微信添加": 0.1,
                "约束遵守": 0.2
            },
            required_steps=[
                "确认负责人身份",
                "询问是否知情低延迟线路",
                "解释标准与低延迟区别及价格",
                "询问发布方式并引导",
                "检查学员端费用",
                "企业微信添加",
                "结束祝福"
            ],
            constraints=[
                "每次回复15-20字",
                "频繁给商家发言机会",
                "被打断时使用过渡语",
                "不说语气词",
                "不承诺优惠券",
                "商家忙时说'就1分钟'",
                "商家开车时礼貌挂断"
            ]
        )