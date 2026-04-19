def generate_breathing_guidance(stress_level="low"):
  
    return {
        "type": "box_breathing",
        "steps": ["吸气4秒", "屏息4秒", "呼气4秒", "屏息4秒"],
        "duration": "5分钟",
        "instruction": "请跟随节奏进行箱式呼吸，有助于稳定心率。"
    }