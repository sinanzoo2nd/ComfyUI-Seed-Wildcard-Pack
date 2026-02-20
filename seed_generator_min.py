import random

class SeedGeneratorWithMin:
    """
    입력된 시드가 1 미만(0일 경우)일 때, 
    1부터 0xffffffffffffffff 사이의 새로운 무작위 난수를 생성하여 반환합니다.
    """
    
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # 프론트엔드에서 음수를 생성하지 못하도록 min을 0으로 수정 (Impact Pack 충돌 방지)
                "seed": ("INT", {"default": 1, "min": 0, "max": 0xffffffffffffffff}),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT", "STRING")
    RETURN_NAMES = ("SEED_INT", "SEED_FLOAT", "SEED_STRING")
    FUNCTION = "generate_seed"
    CATEGORY = "Custom/Wildcard"

    def generate_seed(self, seed):
        # 1 미만의 값(0)이 들어오면 무조건 새로운 난수 발급
        if seed < 1:
            seed = random.randint(1, 0xffffffffffffffff)
        
        return (seed, float(seed), str(seed))

# 노드 매핑
NODE_CLASS_MAPPINGS = {
    "SeedGeneratorWithMin": SeedGeneratorWithMin
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SeedGeneratorWithMin": "Seed Generator (Strict Random)"
}