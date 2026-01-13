class ResizeByScale:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "resize_method": (
                    ["Lanczos", "Bicubic", "Bilinear", "Nearest"],
                    {"default": "Lanczos"}
                ),
                "base_width": ("INT", {"default": 512, "min": 0, "max": 4096}),
                "base_height": ("INT", {"default": 512, "min": 0, "max": 4096}),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0}),
                "crop": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "resize"
    CATEGORY = "image/resize"

    def convert_to_numpy(self, img):
        import numpy as np
        from PIL import Image
        import torch

        if isinstance(img, np.ndarray):
            return img
        elif isinstance(img, Image.Image):
            return np.array(img)
        elif isinstance(img, torch.Tensor):
            img = img.detach().cpu().numpy()
            if img.shape[0] in [1, 3]:  # CHW → HWC
                img = np.transpose(img, (1, 2, 0))
            img = (img * 255).clip(0, 255).astype(np.uint8)
            return img
        else:
            raise TypeError(f"Unsupported image type: {type(img)}")

    def resize(self, image, resize_method, base_width, base_height, scale, crop):
        import cv2
        import numpy as np
        import torch

        # 계산된 해상도
        new_width = int(base_width * scale)
        new_height = int(base_height * scale)

        # 최소 크기 보장 (Conv Layer가 터지지 않게)
        MIN_WIDTH = 16
        MIN_HEIGHT = 16
        new_width = max(new_width, MIN_WIDTH)
        new_height = max(new_height, MIN_HEIGHT)

        # 보간법 설정
        method_map = {
            "Lanczos": cv2.INTER_LANCZOS4,
            "Bicubic": cv2.INTER_CUBIC,
            "Bilinear": cv2.INTER_LINEAR,
            "Nearest": cv2.INTER_NEAREST,
        }
        interpolation = method_map.get(resize_method, cv2.INTER_LANCZOS4)

        resized_images = []
        for img in image:
            np_img = self.convert_to_numpy(img)
            resized = cv2.resize(np_img, (new_width, new_height), interpolation=interpolation)

            if crop:
                if new_width < base_width or new_height < base_height:
                    print("⚠️ Crop skipped: resized image is smaller than base dimensions.")
                else:
                    start_x = (new_width - base_width) // 2
                    start_y = (new_height - base_height) // 2
                    end_x = start_x + base_width
                    end_y = start_y + base_height
                    resized = resized[start_y:end_y, start_x:end_x]

            resized_images.append(resized)

        # numpy → torch.Tensor (B, C, H, W)
        tensor_images = []
        for img in resized_images:
            img = img.transpose(2, 0, 1)  # HWC → CHW
            img = torch.from_numpy(img).float() / 255.0
            tensor_images.append(img)

        if len(tensor_images) == 1:
            batch_tensor = tensor_images[0].unsqueeze(0)  # (1, C, H, W)
        else:
            batch_tensor = torch.stack(tensor_images)     # (B, C, H, W)

        print(f"[DEBUG] Final tensor shape: {batch_tensor.shape}")
        return (batch_tensor,)

NODE_CLASS_MAPPINGS = {
    "ResizeByScale": ResizeByScale
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ResizeByScale": "Resize Image by Base + Scale + Crop"
}
