import json
import os

class UserParams:
    def __init__(self, params_file=None):
        if params_file is None:
            params_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "params.json")
        self.params_file = params_file
        self.data = self._load()
    
    def _load(self):
        if not os.path.exists(self.params_file):
            return {
            "delivery_scenario": {
                "personality": "random",
                "max_turns": 12,
                "interrupt_probability": 0.2,
                "temperature": 0.8,
                "X": 5,
                "Y": 3,
                "Z": 22,
                "W": 7,
                "reward": 2
            },
            "course_scenario": {
                "personality": "random",
                "max_turns": 12,
                "interrupt_probability": 0.15,
                "temperature": 0.8
            }
            }            
        with open(self.params_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def get_delivery_params(self):
        return self.data.get("delivery_scenario", {})
    
    def get_course_params(self):
        return self.data.get("course_scenario", {})

user_params = UserParams()