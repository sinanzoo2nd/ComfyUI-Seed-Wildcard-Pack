import os
import random
import re  # [추가됨] 정규표현식 모듈 임포트

class AnimaArtistFormatter:
    """
    쉼표로 구분된 작가 텍스트를 받아 (@작가이름:2.0) 형태로 포맷팅합니다.
    (작가이름:0.8) 형태의 가중치가 포함되어 있어도 순수 이름만 추출하여 포맷팅합니다.
    원본 텍스트도 함께 출력합니다.
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "target_weight": ("FLOAT", {"default": 2.0, "min": 0.0, "max": 10.0, "step": 0.01}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("formatted_text", "text")
    FUNCTION = "format_text"
    CATEGORY = "Anima/Text"

    def format_text(self, text, target_weight):
        if not text:
            return ("", "")
            
        # API 통신 중 문자열(str)로 전달되더라도 강제로 실수(float)로 변환하여 오류 원천 차단
        target_weight = float(target_weight)
        
        tags = [t.strip() for t in text.split(',')]
        formatted_tags = []
        
        for t in tags:
            if not t:
                continue
                
            # 정규식: ^\( (.+) : [숫자.숫자] \)$ 패턴을 찾습니다.
            match = re.match(r'^\((.+):[0-9.]+\)$', t)
            
            if match:
                # (asanagi:0.8) 형태라면 'asanagi'만 추출
                base_artist = match.group(1).strip()
            else:
                # 가중치가 없는 일반 텍스트라면 그대로 사용
                base_artist = t
                
            formatted_tags.append(f"(@{base_artist}:{round(target_weight, 2)})")
            
        formatted_result = ", ".join(formatted_tags)
        
        return (formatted_result, text)

class AnimaRandomArtistSelector:
    """
    텍스트 파일에서 지정된 수만큼 작가를 중복 없이 랜덤으로 추출합니다.
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "mode": (["Core Artist", "Recommend Artist"],),
                "count": ("INT", {"default": 1, "min": 1, "max": 5, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("artist_text",)
    FUNCTION = "select_artists"
    CATEGORY = "Anima/Text"

    def select_artists(self, mode, count, seed):
        random.seed(seed)
        current_dir = os.path.dirname(os.path.realpath(__file__))
        
        if mode == "Core Artist":
            file_path = os.path.join(current_dir, "Artist_Core.txt")
        else:
            file_path = os.path.join(current_dir, "Artist_Recommend.txt")
            
        artists = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        cleaned = line.strip()
                        if cleaned:
                            artists.append(cleaned)
            except Exception as e:
                print(f"File read error: {e}")
                
        if not artists:
            return ("None",)
            
        actual_count = min(count, len(artists))
        chosen = random.sample(artists, actual_count)
        return (", ".join(chosen),)

NODE_CLASS_MAPPINGS = {
    "AnimaArtistFormatter": AnimaArtistFormatter,
    "AnimaRandomArtistSelector": AnimaRandomArtistSelector
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaArtistFormatter": "🎨 Anima Artist Formatter",
    "AnimaRandomArtistSelector": "🎲 Anima Random Artist Selector"
}