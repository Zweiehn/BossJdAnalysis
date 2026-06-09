"""AI 分析抽象基类 - 定义统一的AI分析接口"""

from abc import ABC, abstractmethod


class BaseAI(ABC):
    """AI分析引擎抽象基类"""

    @abstractmethod
    def analyze_jd(self, raw_text: str) -> dict:
        """
        分析JD文本，返回结构化数据

        Args:
            raw_text: OCR提取的原始JD文本

        Returns:
            包含结构化字段的字典，键为中文字段名

        Raises:
            RuntimeError: API调用失败
            ValueError: 返回数据格式异常
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """返回AI引擎名称"""
        pass
