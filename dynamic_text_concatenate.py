class DynamicTextConcatenate:
    @classmethod
    def INPUT_TYPES(cls):
        num_slots = 10
        base_inputs = {
            "required": {
                "num_inputs": ("INT", {
                    "default": 2,
                    "min": 2,
                    "max": num_slots
                }),
                "delimiter": ("STRING", {
                    "default": "",
                    "multiline": False
                })
            }
        }

        dynamic_inputs = {
            f"text_{i}": ("STRING",) for i in range(1, num_slots + 1)
        }

        return {**base_inputs, "optional": dynamic_inputs}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("concatenated_text",)
    FUNCTION = "concatenate"
    CATEGORY = "Custom/Text"

    def concatenate(self, num_inputs=2, delimiter="", **kwargs):
        texts = []
        for i in range(1, num_inputs + 1):
            text = kwargs.get(f"text_{i}", "")
            texts.append(text or "")
        result = delimiter.join(texts)
        return (result,)


NODE_CLASS_MAPPINGS = {
    "DynamicTextConcatenate": DynamicTextConcatenate
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DynamicTextConcatenate": "🔗 Dynamic Text Concatenate"
}
