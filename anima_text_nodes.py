import os
import json
import re
import urllib.parse
import requests
from server import PromptServer
from aiohttp import web

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



# --- 1. 전역 캐시 (워크플로우 실행 시 중복 호출 방지) ---
DANBOORU_CACHE = {}

# --- 2. Danbooru 파싱 핵심 로직 (Streamlit 로직과 동일) ---
def fetch_and_categorize(url):
    match = re.search(r'/posts/(\d+)', url)
    if not match:
        return None, "유효한 Danbooru 게시물 URL이 아닙니다."
    
    post_id = match.group(1)
    if post_id in DANBOORU_CACHE:
        return DANBOORU_CACHE[post_id], "success"

    original_api_url = f"https://danbooru.donmai.us/posts/{post_id}.json"
    encoded_url = urllib.parse.quote(original_api_url)
    proxy_url = f"https://api.codetabs.com/v1/proxy?quest={encoded_url}"
    headers = {'User-Agent': 'AnimaGeneratorApp/1.0 (by sinanzoo2nd@gmail.com)'}
    
    try:
        response = requests.get(proxy_url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return None, f"프록시 우회 호출 실패: {e}"

    base_dir = os.path.dirname(os.path.abspath(__file__))
    category_json_path = os.path.join(base_dir, "tag_category.json")
    
    cat_data = {}
    if os.path.exists(category_json_path):
        with open(category_json_path, 'r', encoding='utf-8') as f:
            cat_data = json.load(f)

    categorized = {}
    if data.get("tag_string_artist"): categorized["artist"] = data.get("tag_string_artist").split()
    if data.get("tag_string_character"): categorized["character"] = data.get("tag_string_character").split()
    if data.get("tag_string_copyright"): categorized["copyright"] = data.get("tag_string_copyright").split()

    general_tags = data.get("tag_string_general", "").split()
    uncategorized = []
    
    for t in general_tags:
        if not t: continue
        cat_list = cat_data.get(t)
        if cat_list and isinstance(cat_list, list) and len(cat_list) > 0:
            cat = cat_list[0]
            if cat not in categorized: categorized[cat] = []
            categorized[cat].append(t)
        else:
            uncategorized.append(t)
            
    if uncategorized: categorized["uncategorized"] = uncategorized
    
    DANBOORU_CACHE[post_id] = categorized
    return categorized, "success"

# --- 3. ComfyUI 커스텀 API 라우터 (버튼 클릭 시 호출됨) ---
@PromptServer.instance.routes.post("/anima/danbooru_analyze")
async def analyze_danbooru_api(request):
    post_data = await request.json()
    url = post_data.get("url", "")
    categorized, msg = fetch_and_categorize(url)
    
    if categorized:
        return web.json_response({"status": "success", "data": categorized})
    else:
        return web.json_response({"status": "error", "message": msg})

# --- 4. ComfyUI 노드 정의 ---
class DanbooruTagImporter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "url": ("STRING", {"default": "https://danbooru.donmai.us/posts/..."}),
                # 18개 카테고리 스위치
                "artist": ("BOOLEAN", {"default": True}),
                "character": ("BOOLEAN", {"default": True}),
                "copyright": ("BOOLEAN", {"default": True}),
                "person": ("BOOLEAN", {"default": True}),
                "species_traits": ("BOOLEAN", {"default": True}),
                "body": ("BOOLEAN", {"default": True}),
                "face": ("BOOLEAN", {"default": True}),
                "hair": ("BOOLEAN", {"default": True}),
                "appearance": ("BOOLEAN", {"default": True}),
                "clothing": ("BOOLEAN", {"default": True}),
                "accessory": ("BOOLEAN", {"default": True}),
                "state_emotion": ("BOOLEAN", {"default": True}),
                "pose": ("BOOLEAN", {"default": True}),
                "action": ("BOOLEAN", {"default": True}),
                "camera_composition": ("BOOLEAN", {"default": True}),
                "background": ("BOOLEAN", {"default": True}),
                "environment": ("BOOLEAN", {"default": True}),
                "uncategorized": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                # 프론트엔드 버튼 클릭 시 분석 결과가 표시될 숨김/더미 텍스트박스
                "preview_box": ("STRING", {"multiline": True, "default": "버튼을 눌러 분석하세요."}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("ARTIST_PROMPT", "CHARACTER_PROMPT", "BACKGROUND_PROMPT", "ALL_RAW_TAGS")
    FUNCTION = "execute"
    CATEGORY = "Anima/Text"

    def execute(self, url, artist, character, copyright, person, species_traits, body, face, hair, appearance, 
                clothing, accessory, state_emotion, pose, action, camera_composition, background, environment, 
                uncategorized, preview_box=""):
        
        # 1. 태그 파싱 (버튼을 눌렀을 때 저장된 캐시가 있다면 즉시 로드됨)
        categorized, msg = fetch_and_categorize(url)
        if not categorized:
            return ("", "", "", f"Error: {msg}")

        # 2. 스위치 상태 매핑 (딕셔너리 키는 JSON의 카테고리 명과 정확히 일치해야 함)
        active_cats = {
            "artist": artist, 
            "character": character, 
            "copyright": copyright, 
            "person": person,
            "species & traits": species_traits, 
            "body": body, 
            "face": face, 
            "hair": hair, 
            "appearance": appearance, 
            "clothing": clothing, 
            "accessory": accessory, 
            "state & emotion": state_emotion, 
            "pose": pose, 
            "action": action, 
            "camera & composition": camera_composition, 
            "background": background, 
            "environment": environment, 
            "uncategorized": uncategorized
        }

        # 3. 포맷팅 도우미: 언더바를 공백으로, 괄호는 이스케이프 처리
        def format_tags(tags_list):
            return [t.replace('_', ' ').replace('(', r'\(').replace(')', r'\)') for t in tags_list]

        # 4. 문자열 결합 도우미: 카테고리 단위로 줄바꿈(,\n)
        def build_prompt(cat_order):
            lines = []
            for cat in cat_order:
                if active_cats.get(cat, False) and cat in categorized:
                    formatted = format_tags(categorized[cat])
                    if formatted:
                        lines.append(", ".join(formatted))
            return ",\n".join(lines) if lines else ""

        # --- [최종 출력 그룹화] ---
        
        # [Output 1] 메인 작가
        artist_prompt = build_prompt(["artist"])

        # [Output 2] 캐릭터 (앱과 동일한 우선순위 정렬 적용)
        char_order = [
            "person", "copyright", "character", "species & traits", "body", 
            "face", "hair", "appearance", "clothing", "accessory", 
            "state & emotion", "pose", "action", "uncategorized"
        ]
        character_prompt = build_prompt(char_order)

        # [Output 3] 배경 및 구도
        bg_order = ["camera & composition", "background", "environment"]
        background_prompt = build_prompt(bg_order)

        # [Output 4] 전체 Raw 태그 (스위치 상태와 무관하게 모든 태그를 포맷팅하여 1줄로 출력)
        all_raw_list = []
        for cat, tags in categorized.items():
            all_raw_list.extend(format_tags(tags))
        all_raw_tags = ", ".join(all_raw_list)

        return (artist_prompt, character_prompt, background_prompt, all_raw_tags)


# 기존 노드들과 새로 만든 DanbooruTagImporter를 하나의 딕셔너리로 병합합니다.
NODE_CLASS_MAPPINGS = {
    "AnimaRandomArtistSelector": AnimaRandomArtistSelector,
    "AnimaArtistFormatter": AnimaArtistFormatter,
    "DanbooruTagImporter": DanbooruTagImporter
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaRandomArtistSelector": "Anima Random Artist Selector",
    "AnimaArtistFormatter": "Anima Artist Formatter",
    "DanbooruTagImporter": "Danbooru Tag Importer (Anima)"
}