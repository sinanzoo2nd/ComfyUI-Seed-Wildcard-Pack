import os
import folder_paths
import random
import re

class SeedBasedWildcardLora:
    """
    와일드카드 텍스트 파일(Impact Pack 경로)을 읽어 시드 기반으로 줄을 선택하고,
    <lora:name:strength> 구문을 파싱하여 LORA_STACK과 정제된 텍스트를 반환하는 노드.
    (ComfyUI 내부 파일 목록과 대조하여 정확한 파일명을 찾아내는 매칭 로직 포함)
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
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "wildcard_file": (files, ),
                "seed": ("INT", {"default": 1, "min": 1, "max": 0xffffffffffffffff}),
            },
        }

    RETURN_TYPES = ("LORA_STACK", "STRING", "MODEL", "CLIP")
    RETURN_NAMES = ("lora_stack", "populated_text", "model", "clip")
    FUNCTION = "process"
    CATEGORY = "Custom/Wildcard"

    def process(self, model, clip, wildcard_file, seed):
        file_path = os.path.join(self.base_dir, wildcard_file)

        # 1. 파일 읽기
        lines = self.load_lines(file_path)
        if not lines:
            return ([], "", model, clip)

        # 2. 줄 선택
        n = len(lines)
        index = (seed - 1) % n
        selected_line = lines[index]

        # 3. 와일드카드 처리
        rng = random.Random(seed)
        self.refresh_wildcard_map()
        processed_text = self.resolve_wildcards(selected_line, rng)

        # 4. Lora 구문 추출 및 정식 명칭 매칭
        lora_stack, clean_text = self.extract_loras(processed_text)

        return (lora_stack, clean_text, model, clip)

    # --- Helper Functions ---

    def extract_loras(self, text):
        lora_stack = []
        pattern = r"<lora:([^>]+)>"
        
        matches = re.findall(pattern, text)
        
        # ComfyUI가 인식하고 있는 모든 Lora 파일 목록 가져오기
        available_loras = folder_paths.get_filename_list("loras")
        
        for match in matches:
            if not match: continue

            parts = match.split(':')
            raw_lora_name = parts[0].strip()
            
            if not raw_lora_name: continue

            # [핵심] 사용자가 입력한 이름(raw_name)을 시스템의 정식 명칭(real_name)으로 변환
            real_lora_name = self.find_best_match_lora(raw_lora_name, available_loras)
            
            # 매칭에 실패했더라도 일단 원본 이름을 사용 (단, 경고 출력)
            final_name = real_lora_name if real_lora_name else raw_lora_name
            
            if real_lora_name is None:
                print(f"[Warning] SeedWildcardLora: Could not find strict match for Lora '{raw_lora_name}'. Trying raw name.")

            model_strength = 1.0
            clip_strength = 1.0
            
            if len(parts) > 1 and parts[1].strip():
                try:
                    model_strength = float(parts[1])
                    clip_strength = model_strength 
                except: pass
            
            if len(parts) > 2 and parts[2].strip():
                try:
                    clip_strength = float(parts[2])
                except: pass
            
            lora_stack.append((final_name, model_strength, clip_strength))

        clean_text = re.sub(pattern, "", text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        return lora_stack, clean_text

    def find_best_match_lora(self, input_name, available_list):
        """
        사용자 입력(input_name)과 ComfyUI 파일 목록(available_list)을 비교하여
        가장 적절한 실제 파일명을 반환합니다.
        역슬래시(\)와 슬래시(/), 확장자 유무를 자동으로 보정합니다.
        """
        # 비교를 위해 입력값 정규화 (소문자, 역슬래시->슬래시, 확장자 제거)
        normalized_input = input_name.replace("\\", "/").lower()
        if normalized_input.endswith(".safetensors"):
            normalized_input = normalized_input[:-12]
        elif normalized_input.endswith(".pt"):
            normalized_input = normalized_input[:-3]

        # 1차 시도: 목록에서 정확히 매칭되는 것 찾기
        for filename in available_list:
            # 파일 목록 정규화
            normalized_file = filename.replace("\\", "/").lower()
            file_base = normalized_file
            if file_base.endswith(".safetensors"):
                file_base = file_base[:-12]
            elif file_base.endswith(".pt"):
                file_base = file_base[:-3]
            
            # 경로가 정확히 일치하거나, 파일명이 일치하는 경우
            if normalized_input == file_base:
                return filename

        return None # 못 찾음

    def load_lines(self, path):
        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return [line.strip() for line in f.readlines() if line.strip()]
            except Exception as e:
                print(f"[SeedWildcardLora] Error reading {path}: {e}")
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

        def replace_wildcard(match):
            key = match.group(1)
            if key in self.wildcard_map:
                lines = self.load_lines(self.wildcard_map[key])
                if lines: return rng.choice(lines)
            return match.group(0)

        text = re.sub(r'__([\w\-\s]+)__', replace_wildcard, text)

        if text != original_text:
            return self.resolve_wildcards(text, rng, depth + 1)
        return text

NODE_CLASS_MAPPINGS = {
    "SeedBasedWildcardLora": SeedBasedWildcardLora
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SeedBasedWildcardLora": "Seed Based Wildcard (Lora Stack Output)"
}