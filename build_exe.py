"""执行 PyInstaller 打包（Windows OCR + 可选子进程回退）"""
import os
import sys
import shutil

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 清理旧构建
for d in ["dist", "dist_new", "build", "build_new"]:
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)
for f in os.listdir("."):
    if f.endswith(".spec"):
        os.remove(f)

print("已清理旧构建，开始打包...")

# 用唯一路径防止 COLLECT 阶段冲突
import time
_OUT = f"dist_{int(time.time())}"

args = [
    "pyinstaller",
    "--onedir",
    "--name", "BossJD分析器",
    "--noconsole",
    "--distpath", _OUT,
    "--workpath", f"build_{int(time.time())}",
    # 排除不需要的庞大依赖
    "--exclude-module", "paddle",
    "--exclude-module", "paddleocr",
    "--exclude-module", "cv2",
    "--exclude-module", "skimage",
    "--exclude-module", "imgaug",
    "--exclude-module", "matplotlib",
    # 数据文件
    "--add-data", "config.json;.",
    "--add-data", "ocr/base.py;ocr/",
    "--add-data", "ocr/__init__.py;ocr/",
    "--add-data", "ocr/windows_ocr_impl.py;ocr/",
    "--add-data", "ai;ai",
    "--add-data", "ocr_worker.py;.",
    "main.py",
]

sys.argv = args
from PyInstaller.__main__ import run
run()
