import random

class SafetyLevelNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True}), # on/off 스위치 추가
                "level": (["LEVEL 1", "LEVEL 2", "LEVEL 3", "LEVEL 4"], {"default": "LEVEL 1"}),
                "uncensored": ("BOOLEAN", {"default": False}),
                "random_mode": ("BOOLEAN", {"default": False}), # 랜덤 스위치 추가
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("ANIMA_text", "SDXL_text")
    FUNCTION = "get_tags"
    CATEGORY = "Seed Wildcard/Text"

    @classmethod
    def IS_CHANGED(s, enabled, level, uncensored, random_mode):
        # random_mode가 True일 경우 매번 캐시를 무효화하여 새로 실행되도록 함
        if random_mode:
            return float("nan")
        return ""

    def get_tags(self, enabled, level, uncensored, random_mode):
        # 스위치가 off(False)일 경우 두 출력값을 공백(" ")으로 반환
        if not enabled:
            return (" ", " ")

        # 랜덤 모드가 켜진 경우 기존 입력을 덮어씀 (백엔드 비활성화)
        if random_mode:
            level = random.choice(["LEVEL 1", "LEVEL 2", "LEVEL 3", "LEVEL 4"])
            # LEVEL 4가 뽑힌 경우에만 uncensored를 강제로 켬
            uncensored = (level == "LEVEL 4")

        # 레벨별 기본 태그 할당
        if level == "LEVEL 1":
            anima_tags = "safe"
            sdxl_tags = "general"
        elif level == "LEVEL 2":
            anima_tags = "sensitive"
            sdxl_tags = "sensitive"
        elif level == "LEVEL 3":
            anima_tags = "questionable, nsfw"
            sdxl_tags = "questionable, nsfw"
        elif level == "LEVEL 4":
            anima_tags = "explicit"
            sdxl_tags = "explicit"
        else:
            anima_tags, sdxl_tags = "", ""

        # uncensored 스위치 ON(True)일 경우 앞에 텍스트 추가
        if uncensored:
            anima_tags = f"uncensored, {anima_tags}"
            sdxl_tags = f"uncensored, {sdxl_tags}"

        return (str(anima_tags), str(sdxl_tags))

NODE_CLASS_MAPPINGS = {
    "SafetyLevelNode": SafetyLevelNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SafetyLevelNode": "Safety Level Selector"
}