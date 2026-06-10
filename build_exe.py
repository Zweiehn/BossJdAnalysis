"""执行 PyInstaller 打包（PaddleOCR 通过子进程调用，不打包进 exe）"""
import os
import sys
import shutil

# 切换到项目目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 清理旧构建
for d in ["dist", "build"]:
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)
for f in os.listdir("."):
    if f.endswith(".spec"):
        os.remove(f)

print("已清理旧构建，开始打包...")

# PyInstaller 参数
args = [
    "pyinstaller",
    "--onedir",
    "--name", "BossJD分析器",
    "--noconsole",
    "--add-data", "config.json;.",
    "--add-data", "ocr;ocr",                # OCR 抽象基类（不含 PaddleOCR 实现）
    "--add-data", "ai;ai",                   # AI 模块
    "--add-data", "ocr_worker.py;.",         # OCR Worker 脚本（exe 调用它）
    "main.py",
]

sys.argv = args
from PyInstaller.__main__ import run
run()
