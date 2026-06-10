"""Tesseract OCR 实现 - 轻量级 OCR 引擎，适合 PyInstaller 打包"""

import os
import subprocess
from .base import BaseOCR


class TesseractEngine(BaseOCR):
    """Tesseract OCR 引擎封装，支持中文识别"""

    def __init__(self, tesseract_path: str = None, lang: str = "chi_sim+eng"):
        """
        Args:
            tesseract_path: tesseract.exe 路径，None 则从 PATH 查找
            lang: 识别语言，默认中文+英文
        """
        self._tesseract_cmd = tesseract_path or self._find_tesseract()
        self._lang = lang
        self._pytesseract = None

    def _find_tesseract(self) -> str:
        """查找 tesseract 可执行文件"""
        # 1. 检查 exe 同目录下的 tesseract/
        base = os.path.dirname(os.path.abspath(__file__))
        for _ in range(3):
            parent = os.path.dirname(base)
            if os.path.exists(os.path.join(parent, "tesseract", "tesseract.exe")):
                return os.path.join(parent, "tesseract", "tesseract.exe")
            base = parent

        # 2. 环境变量
        for p in os.environ.get("PATH", "").split(";"):
            exe = os.path.join(p, "tesseract.exe")
            if os.path.exists(exe):
                return exe

        # 3. 默认路径
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c

        return "tesseract"  # 最后尝试从 PATH 调用

    def _lazy_init(self):
        """延迟初始化 pytesseract"""
        if self._pytesseract is None:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd
                self._pytesseract = pytesseract
            except ImportError:
                raise RuntimeError(
                    "pytesseract 未安装，请运行: pip install pytesseract"
                )

    def extract_text(self, image_path: str) -> str:
        """
        从图片中提取文本

        Args:
            image_path: 图片文件路径

        Returns:
            提取到的纯文本内容
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        self._lazy_init()

        try:
            # 先尝试用 pytesseract
            text = self._pytesseract.image_to_string(
                image_path, lang=self._lang
            )
            return text.strip()

        except Exception as e:
            # 如果 pytesseract 失败，回退到 subprocess 直接调用
            try:
                result = subprocess.run(
                    [self._tesseract_cmd, image_path, "stdout", "-l", self._lang],
                    capture_output=True, text=True, timeout=60,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
                raise RuntimeError(f"Tesseract 返回错误: {result.stderr[:200]}")
            except FileNotFoundError:
                raise RuntimeError(
                    f"未找到 Tesseract: {self._tesseract_cmd}\n"
                    "请将 Tesseract-OCR 放在程序同目录的 tesseract/ 文件夹中"
                )
            except subprocess.TimeoutExpired:
                raise RuntimeError("Tesseract 识别超时")
            except Exception as e2:
                raise RuntimeError(f"OCR 识别失败: {e2}")

    def get_name(self) -> str:
        return f"Tesseract ({self._lang})"
