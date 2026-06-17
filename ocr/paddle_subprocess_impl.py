"""PaddleOCR 子进程模式 - exe 通过 subprocess 调用系统 Python 执行 OCR"""

import os
import sys
import json
import subprocess
from .base import BaseOCR

# 脚本模式下的 OCR Worker 路径（项目根目录）
_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKER_SCRIPT = os.path.join(_SCRIPT_DIR, "ocr_worker.py")


class PaddleSubprocessEngine(BaseOCR):
    """PaddleOCR 子进程引擎（解决 PyInstaller 打包问题）"""

    def __init__(self, lang: str = "ch", python_cmd: str = None):
        """
        Args:
            lang: 语言
            python_cmd: Python 命令，默认自动查找
        """
        self._lang = lang
        self._python_cmd = python_cmd or self._find_python()

    def _find_python(self) -> str:
        """查找系统 Python（exe模式下跳过内部Python）"""
        candidates = [
            "python",
            "python3",
            r"C:\Python312\python.exe",
            r"C:\Python311\python.exe",
            r"C:\Python310\python.exe",
        ]
        # 脚本模式才加入当前 Python
        if not getattr(sys, "frozen", False):
            candidates.insert(0, sys.executable)
        for cmd in candidates:
            try:
                r = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
                if r.returncode == 0 and "Python" in r.stdout:
                    return cmd
            except Exception:
                continue
        return "python"  # 最后尝试

    def extract_text(self, image_path: str) -> str:
        """
        从图片中提取文本（通过子进程调用 PaddleOCR）

        Args:
            image_path: 图片路径

        Returns:
            提取的文本
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        # 找到 worker 脚本（exe 模式下在 _internal/ 目录）
        worker = None
        if getattr(sys, "frozen", False):
            candidates = [
                os.path.join(os.path.dirname(sys.executable), "ocr_worker.py"),
                os.path.join(os.path.dirname(sys.executable), "_internal", "ocr_worker.py"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    worker = c
                    break
        else:
            worker = WORKER_SCRIPT

        if not worker or not os.path.exists(worker):
            raise RuntimeError(
                f"OCR Worker 脚本不存在，请确保 ocr_worker.py 在程序目录中"
            )

        try:
            result = subprocess.run(
                [self._python_cmd, worker, image_path],
                capture_output=True, text=True, timeout=120,
            )

            if result.returncode != 0:
                err = result.stderr.strip()[:300]
                raise RuntimeError(f"OCR 子进程失败: {err}")

            # stdout 第一行是 OCR 文本
            output = result.stdout.strip()
            if not output:
                return ""
            return output

        except FileNotFoundError:
            raise RuntimeError(
                f"未找到 Python ({self._python_cmd})，请确保已安装 Python 和 PaddleOCR\n"
                "运行: pip install paddlepaddle paddleocr"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("OCR 识别超时（超过120秒）")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"OCR 子进程异常: {e}")

    def get_name(self) -> str:
        return f"PaddleOCR (子进程模式)"
