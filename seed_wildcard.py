import os
import folder_paths
import random
import re

class SeedBasedWildcardImpact:
    def __init__(self):
        self.wildcard_map = {}
        # Impact Pack 경로 추정
        self.base_dir = os.path.join(folder_paths.base_path, "custom_nodes", "ComfyUI-Impact-Pack", "wildcards")
        print(f"\n[Debug] Initialized. Target Wildcard Dir: {self.base_dir}")

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
                "seed": ("INT", {"default": 1, "min": 1, "max": 0xffffffffffffffff}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("selected_text",)
    FUNCTION = "process"
    CATEGORY = "Custom/Wildcard"

    def process(self, wildcard_file, seed):
        file_path = os.path.join(self.base_dir, wildcard_file)
        
        # 1. 맵 갱신 (소문자 키 사용)
        self.refresh_wildcard_map()

        lines = self.load_lines(file_path)
        if not lines:
            return ("",)

        n = len(lines)
        index = (seed - 1) % n
        selected_line = lines[index]
        
        # print(f"[Debug] Processing Line: {selected_line}") # 너무 시끄러우면 주석 처리

        rng = random.Random(seed)
        
        final_text = self.resolve_wildcards(selected_line, rng)
        
        return (final_text,)

    def load_lines(self, path):
        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                    return lines
            except Exception as e:
                print(f"[Debug] Error reading file {path}: {e}")
        return []

    def refresh_wildcard_map(self):
        self.wildcard_map = {}
        if os.path.exists(self.base_dir):
            for root, dirs, filenames in os.walk(self.base_dir):
                for filename in filenames:
                    if filename.endswith('.txt'):
                        # [핵심 수정 1] 키를 무조건 소문자로 변환하여 저장
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

        # 2. Wildcard File (__tag__)
        def replace_wildcard(match):
            full_tag = match.group(1)
            basename = os.path.basename(full_tag)
            
            # [핵심 수정 2] 찾는 키도 무조건 소문자로 변환
            key = os.path.splitext(basename)[0].lower()

            if key in self.wildcard_map:
                target_path = self.wildcard_map[key]
                lines = self.load_lines(target_path)
                if lines:
                    return rng.choice(lines)
            
            # 파일을 못 찾았으면 원본 텍스트 반환
            return match.group(0)

        # 정규표현식: 점(.)과 슬래시(/, \) 포함
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