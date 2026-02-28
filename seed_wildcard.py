import os
import folder_paths
import random
import re

class SeedBasedWildcardImpact:
    """
    ComfyUI-Impact-Pack의 wildcards 폴더 내 .txt 파일을 선택하고,
    시드값에 따라 특정 줄을 반환한 뒤, 
    해당 줄에 포함된 와일드카드 구문(__tag__, {a|b})을 처리하는 노드.
    (기능: 경로 포함 태그 지원, 대소문자 무시 매칭, 재귀 호출, 음수 시드 방어)
    """
    
    def __init__(self):
        self.wildcard_map = {}
        self.base_dir = os.path.join(folder_paths.base_path, "custom_nodes", "ComfyUI-Impact-Pack", "wildcards")

    @classmethod
    def INPUT_TYPES(s):
        wildcard_dir = os.path.join(folder_paths.base_path, "custom_nodes", "ComfyUI-Impact-Pack", "wildcards")
        
        files = []
        if os.path.exists(wildcard_dir):
            for root, dirs, filenames in os.walk(wildcard_dir):
                for filename in filenames:
                    if filename.endswith('.txt'):
                        full_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(full_path, wildcard_dir)
                        files.append(rel_path)
            files.sort()
            
        if not files:
            files = ["no_txt_files_found.txt"]

        return {
            "required": {
                "wildcard_file": (files, ), 
                # min값은 UI상 제한일 뿐, 입력으로 들어오는 값은 음수일 수 있음
                "seed": ("INT", {"default": 1, "min": -0xffffffffffffffff, "max": 0xffffffffffffffff}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("selected_text",)
    FUNCTION = "process"
    CATEGORY = "Custom/Wildcard"

    def process(self, wildcard_file, seed):
        file_path = os.path.join(self.base_dir, wildcard_file)
        
        # [핵심 수정] 입력된 시드가 음수라면 양수로 변환 (Impact Pack과의 호환성 및 안전성 확보)
        seed = abs(seed)

        # 맵 갱신
        self.refresh_wildcard_map()

        lines = self.load_lines(file_path)
        if not lines:
            return ("",)

        n = len(lines)
        # 시드는 1부터 시작하는 것으로 간주하여 인덱스 계산
        index = (seed - 1) % n
        selected_line = lines[index]
        
        rng = random.Random(seed)
        final_text = self.resolve_wildcards(selected_line, rng)
        
        return (final_text,)

    def load_lines(self, path):
        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return [line.strip() for line in f.readlines() if line.strip()]
            except Exception as e:
                print(f"[SeedWildcard] Error reading {path}: {e}")
        return []

    def refresh_wildcard_map(self):
        self.wildcard_map = {}
        if os.path.exists(self.base_dir):
            for root, dirs, filenames in os.walk(self.base_dir):
                for filename in filenames:
                    if filename.endswith('.txt'):
                        key = os.path.splitext(filename)[0].lower()
                        self.wildcard_map[key] = os.path.join(root, filename)

    def resolve_wildcards(self, text, rng, depth=0):
        if depth > 20: 
            return text

        original_text = text

        # 1. Dynamic Prompts
        while True:
            match = re.search(r'\{([^{}]+)\}', text)
            if not match: break
            content = match.group(1)
            segments = content.split('|')
            options = []
            weights = []
            for segment in segments:
                if '::' in segment:
                    try:
                        weight_str, val = segment.split('::', 1)
                        weight = float(weight_str)
                    except ValueError:
                        weight = 1.0
                        val = segment
                else:
                    weight = 1.0
                    val = segment
                options.append(val)
                weights.append(weight)
            try:
                choice = rng.choices(options, weights=weights, k=1)[0]
            except ValueError:
                choice = options[0] if options else ""
            text = text[:match.start()] + choice + text[match.end():]

        # 2. Wildcard File
        def replace_wildcard(match):
            full_tag = match.group(1)
            basename = os.path.basename(full_tag)
            key = os.path.splitext(basename)[0].lower()

            if key in self.wildcard_map:
                target_path = self.wildcard_map[key]
                lines = self.load_lines(target_path)
                if lines:
                    return rng.choice(lines)
            
            return match.group(0)

        text = re.sub(r'__([\w\-\s./\\]+)__', replace_wildcard, text)

        if text != original_text:
            return self.resolve_wildcards(text, rng, depth + 1)
        
        return text

NODE_CLASS_MAPPINGS = {
    "SeedBasedWildcardImpact": SeedBasedWildcardImpact
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SeedBasedWildcardImpact": "Seed Based Wildcard (Impact & Weighted)"
}