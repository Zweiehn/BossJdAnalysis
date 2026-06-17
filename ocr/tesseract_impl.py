"""Tesseract OCR 实现 - 轻量级 OCR 引擎，适合 PyInstaller 打包"""

import os
import sys
import subprocess
from .base import BaseOCR


class TesseractEngine(BaseOCR):
    """Tesseract OCR 引擎封装，支持中文识别，支持 exe 内嵌便携版"""

    def __init__(self, tesseract_path: str = None, lang: str = "chi_sim+eng"):
        """
        Args:
            tesseract_path: tesseract.exe 路径，None 则自动查找
            lang: 识别语言，默认中文+英文
        """
        self._tesseract_cmd = tesseract_path or self._find_tesseract()
        self._lang = lang
        self._pytesseract = None

    def _find_tesseract(self) -> str:
        """查找 tesseract 可执行文件（优先 exe 同目录的便携版）"""
        frozen = getattr(sys, "frozen", False)
        app_dir = os.path.dirname(sys.executable) if frozen else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        internal_dir = os.path.join(app_dir, "_internal") if frozen else ""

        # 检测路径列表
        candidates = []
        # exe 同目录
        candidates.append(os.path.join(app_dir, "tesseract_portable", "tesseract.exe"))
        candidates.append(os.path.join(app_dir, "tesseract", "tesseract.exe"))
        # _internal 目录（PyInstaller 打包）
        if internal_dir:
            candidates.append(os.path.join(internal_dir, "tesseract_portable", "tesseract.exe"))
            candidates.append(os.path.join(internal_dir, "tesseract", "tesseract.exe"))
        # exe 同目录下的多种命名
        candidates.append(os.path.join(app_dir, "tesseract.exe"))

        for c in candidates:
            if os.path.exists(c):
                return c

        # 3. 环境变量
        for p in os.environ.get("PATH", "").split(";"):
            exe = os.path.join(p, "tesseract.exe")
            if os.path.exists(exe):
                return exe

        # 4. 默认安装路径
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c

        return "tesseract"  # 最后尝试从 PATH 调用

    def _get_tessdata_dir(self) -> str:
        """获取 tessdata 目录路径（搜索 exe 同目录和 _internal）"""
        search_dirs = [
            os.path.dirname(self._tesseract_cmd),  # tesseract 所在目录
            os.path.join(os.path.dirname(self._tesseract_cmd), ".."),  # 上级目录
        ]
        frozen = getattr(sys, "frozen", False)
        if frozen:
            app_dir = os.path.dirname(sys.executable)
            search_dirs.extend([
                os.path.join(app_dir, "tesseract_portable"),
                os.path.join(app_dir, "_internal", "tesseract_portable"),
                os.path.join(app_dir, "_internal"),
            ])
        for d in search_dirs:
            tessdata = os.path.join(d, "tessdata")
            if os.path.exists(os.path.join(tessdata, "chi_sim.traineddata")):
                return os.path.abspath(tessdata)
        return ""

    def _lazy_init(self):
        """延迟初始化 pytesseract"""
        if self._pytesseract is None:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd
                # 设置语言数据目录（便携版）
                td = self._get_tessdata_dir()
                if td:
                    os.environ["TESSDATA_PREFIX"] = td
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

        env = os.environ.copy()
        td = self._get_tessdata_dir()
        if td:
            env["TESSDATA_PREFIX"] = td

        try:
            text = self._pytesseract.image_to_string(
                image_path, lang=self._lang
            )
            return text.strip()

        except Exception:
            try:
                result = subprocess.run(
                    [self._tesseract_cmd, image_path, "stdout", "-l", self._lang],
                    capture_output=True, text=True, timeout=60, env=env,
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
