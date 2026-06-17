"""执行 PyInstaller 打包（内嵌 Tesseract OCR，解压即用）"""
import os
import sys
import shutil
import time
import glob

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 清理旧构建
for d in ["dist", "dist_new", "build", "build_new"]:
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)
for f in os.listdir("."):
    if f.endswith(".spec"):
        os.remove(f)

print("已清理旧构建，开始打包...")

tess_dir = "tesseract_portable"
_OUT = f"dist_{int(time.time())}"

# 收集 Tesseract 所有文件
tess_files = []
for root, dirs, files in os.walk(tess_dir):
    for f in files:
        src = os.path.join(root, f)
        rel = os.path.relpath(src, tess_dir)
        tess_files.append(f"{src};tesseract_portable/{rel}")

print(f"Tesseract 文件: {len(tess_files)} 个")

args = [
    "pyinstaller",
    "--onedir",
    "--name", "BossJD分析器",
    "--noconsole",
    "--distpath", _OUT,
    "--workpath", f"build_{int(time.time())}",
    # 排除庞大依赖
    "--exclude-module", "paddle",
    "--exclude-module", "paddleocr",
    "--exclude-module", "cv2",
    "--exclude-module", "skimage",
    "--exclude-module", "imgaug",
    "--exclude-module", "matplotlib",
    # 数据文件
    "--add-data", f"config.json;.",
    "--add-data", f"ocr/base.py;ocr/",
    "--add-data", f"ocr/__init__.py;ocr/",
    "--add-data", f"ocr/tesseract_impl.py;ocr/",
    "--add-data", f"ai;ai",
]

# 添加 Tesseract 文件
for tf in tess_files:
    args.extend(["--add-data", tf])

args.append("main.py")

sys.argv = args
from PyInstaller.__main__ import run
run()
