import os
import folder_paths
import random
import re

class SeedBasedWildcardImpact:
    """
    ComfyUI-Impact-Pack의 wildcards 폴더 내 .txt 파일을 선택하고,
    시드값(1 이상)에 따라 특정 줄을 반환한 뒤, 
    해당 줄에 포함된 와일드카드 구문(__tag__, {a|b}, {1::a|9::b})을 재귀적으로 처리하여 반환하는 노드
    """
    
    def __init__(self):
        self.wildcard_map = {}
        # 기본 경로 설정
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
                # [수정됨] 시드값 최소값을 1로 설정, 기본값도 1로 변경
                "seed": ("INT", {"default": 1, "min": 1, "max": 0xffffffffffffffff}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("selected_text",)
    FUNCTION = "process"
    CATEGORY = "Custom/Wildcard"

    def process(self, wildcard_file, seed):
        file_path = os.path.join(self.base_dir, wildcard_file)

        # 1. 메인 파일 읽기
        lines = self.load_lines(file_path)
        if not lines:
            return ("",)

        n = len(lines)
        
        # [수정됨] 시드가 1일 때 0번째 줄(첫 줄)을 가져오도록 보정
        # seed가 1 이상이므로 (seed - 1)을 사용
        index = (seed - 1) % n
        selected_line = lines[index]

        # 2. 와일드카드 처리 (RNG 초기화)
        rng = random.Random(seed)
        
        self.refresh_wildcard_map()
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
                        key = os.path.splitext(filename)[0]
                        self.wildcard_map[key] = os.path.join(root, filename)

    def resolve_wildcards(self, text, rng, depth=0):
        if depth > 20: 
            return text

        original_text = text

        # 1. Dynamic Prompts 처리: {1::option1|2::option2}
        while True:
            match = re.search(r'\{([^{}]+)\}', text)
            if not match:
                break
            
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

        # 2. Wildcard File 처리: __filename__
        def replace_wildcard(match):
            key = match.group(1)
            if key in self.wildcard_map:
                lines = self.load_lines(self.wildcard_map[key])
                if lines:
                    return rng.choice(lines)
            return match.group(0)

        text = re.sub(r'__([\w\-\s]+)__', replace_wildcard, text)

        # 3. 재귀 호출
        if text != original_text:
            return self.resolve_wildcards(text, rng, depth + 1)
        
        return text

# 노드 매핑
NODE_CLASS_MAPPINGS = {
    "SeedBasedWildcardImpact": SeedBasedWildcardImpact
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SeedBasedWildcardImpact": "Seed Based Wildcard (Impact & Weighted)"
}