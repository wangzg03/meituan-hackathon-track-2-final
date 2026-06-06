from .llm_user_simulators import LLMUserSimulator
from param_setting.user_params import user_params

class CourseManagerSimulator(LLMUserSimulator):
    def __init__(self, personality=None):   # 新增参数
        params = user_params.get_delivery_params()
        if personality is None:
            personality = params.get("personality", "random")
        max_turns = params.get("max_turns", 8)
        interrupt_prob = params.get("interrupt_probability", 0.2)
        temperature = params.get("temperature", 0.8)
        if personality == "random":
            personality = None
        super().__init__(
            role="manager",
            name=None,
            max_turns=max_turns,
            interrupt_prob=interrupt_prob,
            temperature=temperature,
            personality=personality
        )
