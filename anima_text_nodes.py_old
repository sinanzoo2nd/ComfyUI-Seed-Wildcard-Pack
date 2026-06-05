import os
import json
import re
import urllib.parse
import requests
import random
from server import PromptServer
from aiohttp import web

class AnimaArtistFormatter:
    """
    ANIMA용: 괄호()나 내부 가중치(:0.8 등)를 강제로 제거하고 (@작가이름:목표가중치)로 포맷팅합니다.
    SDXL용: 사용자가 입력한 괄호와 개별 가중치를 훼손하지 않고 원본 그대로 전달합니다.
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
    # 🌟 SDXL 핀 이름을 직관적으로 변경 (원본 텍스트가 나간다는 의미)
    RETURN_NAMES = ("anima_formatted", "sdxl_original_text")
    FUNCTION = "format_text"
    CATEGORY = "Anima/Text"

    def format_text(self, text, target_weight):
        if not text:
            return ("", "")
            
        try:
            target_weight = float(target_weight)
        except ValueError:
            target_weight = 2.0
            
        # --- ANIMA 엔진용 포맷팅 (강제 정화) ---
        # 1. 텍스트 내의 모든 가중치 숫자 제거 (예: :0.2, :1.5 등)
        clean_text = re.sub(r':\d+(?:\.\d+)?', '', text)
        
        # 2. 이스케이프(\)되지 않은 순수 괄호만 제거
        # Negative Lookbehind (?<!\\) 를 사용하여 앞에 \가 없는 ( 와 ) 만 찾아냅니다.
        clean_text = re.sub(r'(?<!\\)[()]', '', clean_text)
        
        # 3. 쉼표로 분리 후 앞뒤 공백 제거
        tags = [t.strip() for t in clean_text.split(',')]
        
        anima_tags = []
        for base_artist in tags:
            if not base_artist:
                continue
            anima_tags.append(f"(@{base_artist}:{round(target_weight, 2)})")
            
        anima_result = ", ".join(anima_tags)
        
        # --- [Output 2] SDXL 엔진용 텍스트 (원본 유지) ---
        # 🌟 작성자님의 의도대로, 개별 가중치와 괄호가 포함된 원본 텍스트를 그대로 넘깁니다.
        sdxl_result = text.strip()
        
        return (anima_result, sdxl_result)

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

class DanbooruTextCategorizer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "(1girl:1.2), red eyes, touhou \\(project\\)"}),
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
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("ARTIST_PROMPT", "CHARACTER_PROMPT", "BACKGROUND_PROMPT", "ALL_RAW_TAGS")
    FUNCTION = "execute"
    CATEGORY = "Anima/Text"

    def execute(self, text, artist, character, copyright, person, species_traits, body, face, hair, appearance, 
                clothing, accessory, state_emotion, pose, action, camera_composition, background, environment, 
                uncategorized):
        
        # 1. 스마트 파서: 괄호 안의 쉼표는 무시하고 태그 분리
        def split_tags_smart(raw_text):
            result = []
            current = []
            depth = 0
            i = 0
            while i < len(raw_text):
                c = raw_text[i]
                # 이스케이프 처리된 괄호는 무시
                if c == '\\' and i + 1 < len(raw_text):
                    current.append(c)
                    current.append(raw_text[i+1])
                    i += 2
                    continue
                
                if c in '([':
                    depth += 1
                elif c in ')]':
                    depth = max(0, depth - 1)
                
                # 괄호 깊이가 0일 때만 쉼표로 분리
                if c == ',' and depth == 0:
                    result.append(''.join(current).strip())
                    current = []
                else:
                    current.append(c)
                i += 1
            if current:
                result.append(''.join(current).strip())
            return [r for r in result if r]

        raw_tags = split_tags_smart(text)

        # 2. JSON 카테고리 파일 로드
        base_dir = os.path.dirname(os.path.abspath(__file__))
        category_json_path = os.path.join(base_dir, "tag_category.json")
        cat_data = {}
        if os.path.exists(category_json_path):
            with open(category_json_path, 'r', encoding='utf-8') as f:
                cat_data = json.load(f)

        # 3. 그룹 태그 호환용 카테고리 탐색기
        def get_category(raw_str):
            s = raw_str.replace(r'\(', '(').replace(r'\)', ')')
            
            # 외부 가중치 및 괄호 껍데기 제거
            while True:
                m = re.match(r'^([\[\(]+)(.*?)(:\d+(?:\.\d+)?)?([\]\)]+)$', s)
                if m:
                    s = m.group(2)
                else:
                    break
            
            # (A, B, C:1.5) 같은 그룹 태그일 경우 내부를 다시 쪼개서 첫 번째로 매칭되는 카테고리 채택
            sub_tags = [t.strip() for t in s.split(',')]
            for sub in sub_tags:
                lookup_key = sub.replace(' ', '_').lower()
                cat_list = cat_data.get(lookup_key)
                if cat_list and isinstance(cat_list, list) and len(cat_list) > 0:
                    return cat_list[0]
            
            return "uncategorized"

        # 4. 태그 분류 (원본 텍스트 유지)
        categorized = {"uncategorized": []}
        for raw_t in raw_tags:
            if not raw_t: continue
            cat = get_category(raw_t)
            if cat not in categorized: categorized[cat] = []
            categorized[cat].append(raw_t) # 원본 가중치 형태 그대로 저장

        # 5. 스위치 상태 매핑
        active_cats = {
            "artist": artist, "character": character, "copyright": copyright, "person": person,
            "species & traits": species_traits, "body": body, "face": face, "hair": hair, 
            "appearance": appearance, "clothing": clothing, "accessory": accessory, 
            "state & emotion": state_emotion, "pose": pose, "action": action, 
            "camera & composition": camera_composition, "background": background, 
            "environment": environment, "uncategorized": uncategorized
        }

        # 6. 문자열 결합 도우미
        def build_prompt(cat_order):
            lines = []
            for cat in cat_order:
                if active_cats.get(cat, False) and cat in categorized:
                    tags_to_join = categorized[cat]
                    if tags_to_join:
                        lines.append(", ".join(tags_to_join))
            return ",\n".join(lines) if lines else ""

        # --- [최종 출력 그룹화] ---
        artist_prompt = build_prompt(["artist"])

        char_order = [
            "person", "copyright", "character", "species & traits", "body", 
            "face", "hair", "appearance", "clothing", "accessory", 
            "state & emotion", "pose", "action", "uncategorized"
        ]
        character_prompt = build_prompt(char_order)

        bg_order = ["camera & composition", "background", "environment"]
        background_prompt = build_prompt(bg_order)

        all_raw_list = []
        for cat, tags in categorized.items():
            if tags:
                all_raw_list.extend(tags)
        all_raw_tags = ", ".join(all_raw_list)

        return (artist_prompt, character_prompt, background_prompt, all_raw_tags)
        

# 기존 노드들과 새로 만든 DanbooruTagImporter를 하나의 딕셔너리로 병합합니다.
NODE_CLASS_MAPPINGS = {
    "AnimaRandomArtistSelector": AnimaRandomArtistSelector,
    "AnimaArtistFormatter": AnimaArtistFormatter,
    "DanbooruTagImporter": DanbooruTagImporter,
    "DanbooruTextCategorizer": DanbooruTextCategorizer
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaRandomArtistSelector": "Anima Random Artist Selector",
    "AnimaArtistFormatter": "Anima Artist Formatter",
    "DanbooruTagImporter": "Danbooru Tag Importer (Anima)",
    "DanbooruTextCategorizer": "Danbooru Text Categorizer (Anima)"
}