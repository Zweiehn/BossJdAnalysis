"""OCR 抽象基类 - 定义统一的OCR接口"""

from abc import ABC, abstractmethod


class BaseOCR(ABC):
    """OCR引擎抽象基类"""

    @abstractmethod
    def extract_text(self, image_path: str) -> str:
        """
        从图片中提取文本

        Args:
            image_path: 图片文件路径

        Returns:
            提取到的纯文本内容

        Raises:
            FileNotFoundError: 图片不存在
            RuntimeError: OCR 处理失败
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """返回OCR引擎名称"""
        pass
