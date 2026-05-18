import random

class SeedGeneratorWithMin:
    """
    WAS-NS Seed 노드와 유사하지만, '최소값(min_value)' 보정 기능을 강화한 노드.
    1. 입력된 시드가 음수라면 즉시 절대값(양수)으로 변환합니다. (예: -50 -> 50)
    2. 그 후, 설정된 min_value보다 작다면 min_value로 보정합니다. (예: 0 -> 1)
    """
    
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # [수정됨] 음수 입력이 가능하도록 최소값을 확장했습니다.
                # 그래야 'randomize' 시 음수가 나올 수 있고, 아래 로직이 의미가 생깁니다.
                "seed": ("INT", {"default": 1, "min": -0xffffffffffffffff, "max": 0xffffffffffffffff}),
                
                # 최소값 제한 (기본값 1)
                "min_value": ("INT", {"default": 1, "min": 0, "max": 0xffffffffffffffff, "step": 1}),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT", "STRING")
    RETURN_NAMES = ("SEED_INT", "SEED_FLOAT", "SEED_STRING")
    FUNCTION = "generate_seed"
    CATEGORY = "Custom/Wildcard"

    def generate_seed(self, seed, min_value):
        # 1. 절대값 변환 (음수일 경우 양수로 변경)
        # 예: -150 -> 150
        seed = abs(seed)
        
        # 2. 최소값 보정
        # 예: 변환된 150 >= 1 이므로 150 유지
        # 예: 0 >= 1 (거짓) 이므로 1로 보정
        final_seed = max(seed, min_value)
        
        return (final_seed, float(final_seed), str(final_seed))

# 노드 매핑
NODE_CLASS_MAPPINGS = {
    "SeedGeneratorWithMin": SeedGeneratorWithMin
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SeedGeneratorWithMin": "Seed Generator (Min Limit)"
}