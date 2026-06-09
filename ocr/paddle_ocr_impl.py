"""PaddleOCR 实现 - 使用百度PaddleOCR引擎"""

import os
from .base import BaseOCR


class PaddleOCREngine(BaseOCR):
    """PaddleOCR 引擎封装，支持中文长图识别"""

    def __init__(self, lang: str = "ch"):
        """
        Args:
            lang: 语言，默认 "ch"（中文）
        """
        self._lang = lang
        self._ocr = None

    def _lazy_init(self):
        """延迟初始化 OCR 引擎（首次使用时加载模型）"""
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=self._lang,
                    show_log=False,          # 减少控制台输出
                    use_gpu=False,            # 默认使用CPU，稳定兼容
                )
            except ImportError:
                raise RuntimeError(
                    "PaddleOCR 未安装，请运行: pip install paddlepaddle paddleocr"
                )
            except Exception as e:
                raise RuntimeError(f"PaddleOCR 初始化失败: {e}")

    def extract_text(self, image_path: str) -> str:
        """
        从图片中提取文本

        Args:
            image_path: 图片路径

        Returns:
            提取的文本，按阅读顺序排列
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        self._lazy_init()

        try:
            result = self._ocr.ocr(image_path, cls=True)
            if not result or not result[0]:
                return ""

            # 提取文本，按行拼接
            lines = []
            for line in result[0]:
                text = line[1][0]  # (text, confidence)
                if text and text.strip():
                    lines.append(text.strip())

            return "\n".join(lines)

        except Exception as e:
            raise RuntimeError(f"OCR 识别失败 [{os.path.basename(image_path)}]: {e}")

    def extract_text_with_confidence(self, image_path: str) -> list:
        """
        提取文本及置信度（扩展方法）

        Returns:
            [(text, confidence), ...]
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        self._lazy_init()

        try:
            result = self._ocr.ocr(image_path, cls=True)
            if not result or not result[0]:
                return []

            items = []
            for line in result[0]:
                text = line[1][0]
                confidence = line[1][1]
                if text and text.strip():
                    items.append((text.strip(), confidence))

            return items

        except Exception as e:
            raise RuntimeError(f"OCR 识别失败 [{os.path.basename(image_path)}]: {e}")

    def get_name(self) -> str:
        return "PaddleOCR"
