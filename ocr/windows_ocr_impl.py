"""Windows 内置 OCR 引擎 - 使用 Windows.Media.Ocr，无需额外安装"""

import os
import sys
import subprocess
from .base import BaseOCR


# 使用 PowerShell 脚本调用 Windows.Media.Ocr
PS_SCRIPT = r"""
param([string]$ImagePath)

Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile($ImagePath)

# 使用 UWP OCR API
$ocr = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $ocr) {
    $ocr = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('zh-Hans-CN'))
}
if (-not $ocr -or -not $ocr.IsLanguageSupported($ocr.RecognizerLanguage)) {
    Write-Error "Windows OCR 不支持中文或未安装中文OCR语言包"
    exit 1
}

$stream = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync(
    [Windows.Graphics.Imaging.RandomAccessStreamReference]::CreateFromUri([System.Uri]::new($ImagePath))
).GetAwaiter().GetResult()

$bitmap = $stream.GetSoftwareBitmapAsync().GetAwaiter().GetResult()

$result = $ocr.RecognizeAsync($bitmap).GetAwaiter().GetResult()

$lines = @()
foreach ($line in $result.Lines) {
    $text = $line.Text.Trim()
    if ($text) { $lines += $text }
}
Write-Output ($lines -join "`r`n")
"""


class WindowsOCREngine(BaseOCR):
    """Windows 原生 OCR 引擎（基于 Windows.Media.Ocr）"""

    def __init__(self, lang: str = "zh-Hans-CN"):
        self._lang = lang

    def extract_text(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Add-Type -AssemblyName System.Drawing; "
                 f"$img = [System.Drawing.Image]::FromFile('{image_path}'); "
                 f"$w = $img.Width; $h = $img.Height; "
                 f"$ocr = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages(); "
                 f"if (-not $ocr) {{ $ocr = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('{self._lang}')); }} "
                 f"if (-not $ocr) {{ Write-Error 'NO_OCR'; exit 1; }} "
                 f"$stream = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync("
                 f"[Windows.Graphics.Imaging.RandomAccessStreamReference]::CreateFromUri([System.Uri]::new($image_path))"
                 f").GetAwaiter().GetResult(); "
                 f"$bitmap = $stream.GetSoftwareBitmapAsync().GetAwaiter().GetResult(); "
                 f"$result = $ocr.RecognizeAsync($bitmap).GetAwaiter().GetResult(); "
                 f"$result.Text"
                ],
                capture_output=True, text=True, timeout=60,
            )

            if result.returncode != 0:
                err = (result.stderr or "").strip()
                if "NO_OCR" in err:
                    raise RuntimeError(
                        "Windows OCR 不可用\n"
                        "原因：当前系统未安装中文OCR语言包\n"
                        "解决方法：设置 → 时间和语言 → 语言 → 中文 → 选项 → 下载OCR\n"
                        "或安装 PaddleOCR: pip install paddlepaddle paddleocr"
                    )
                raise RuntimeError(f"OCR 失败: {err or '未知错误'}")

            text = (result.stdout or "").strip()
            return text

        except FileNotFoundError:
            raise RuntimeError("未找到 PowerShell，请使用 Windows 10/11")
        except subprocess.TimeoutExpired:
            raise RuntimeError("OCR 识别超时")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"OCR 失败: {e}")

    def get_name(self) -> str:
        return "Windows OCR"
