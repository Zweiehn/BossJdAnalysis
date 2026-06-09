"""截图管理模块 - 保存、命名、管理截图文件"""

import os
import shutil
import re
from datetime import datetime
from config import Config, get_app_dir


class ScreenshotManager:
    """截图文件管理器"""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self._ensure_screenshot_dir()

    def _ensure_screenshot_dir(self):
        """确保截图目录存在"""
        directory = self._get_abs_dir()
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _get_abs_dir(self) -> str:
        """获取截图目录的绝对路径"""
        ss_dir = self.config.screenshot_dir
        if os.path.isabs(ss_dir):
            return ss_dir
        # 相对路径基于应用根目录
        return os.path.join(get_app_dir(), ss_dir)

    def get_screenshot_dir(self) -> str:
        """公开方法：获取截图目录绝对路径"""
        return self._get_abs_dir()

    def _get_next_sequence(self) -> int:
        """获取下一个可用的序号"""
        directory = self._get_abs_dir()
        pattern = re.compile(r"boss_jd_(\d{8})_(\d{3})\.png")
        max_seq = 0
        today = datetime.now().strftime("%Y%m%d")

        if os.path.exists(directory):
            for filename in os.listdir(directory):
                match = pattern.match(filename)
                if match:
                    file_date, seq = match.groups()
                    if file_date == today:
                        max_seq = max(max_seq, int(seq))

        return max_seq + 1

    def save_screenshot(self, source_path: str) -> str:
        """
        保存截图到管理目录

        Args:
            source_path: 源图片路径

        Returns:
            保存后的文件的完整绝对路径 (如 D:/.../screenshots/boss_jd_20260608_001.png)

        Raises:
            FileNotFoundError: 源文件不存在
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"源文件不存在: {source_path}")

        # 生成目标文件名
        today = datetime.now().strftime("%Y%m%d")
        seq = self._get_next_sequence()
        filename = f"boss_jd_{today}_{seq:03d}.png"

        # 转换格式（如果不是png则转换）
        dest_dir = self._get_abs_dir()
        dest_path = os.path.join(dest_dir, filename)

        # 复制文件
        shutil.copy2(source_path, dest_path)
        print(f"截图已保存: {dest_path}")

        return dest_path

    def get_screenshot_path(self, filename: str) -> str:
        """根据文件名获取完整路径"""
        return os.path.join(self._get_abs_dir(), filename)

    def get_all_screenshots(self) -> list:
        """获取所有截图文件列表（按时间排序）"""
        directory = self._get_abs_dir()
        if not os.path.exists(directory):
            return []

        files = [f for f in os.listdir(directory) if f.startswith("boss_jd_") and f.endswith(".png")]
        files.sort()
        return files

    def delete_screenshot(self, filename: str):
        """删除截图文件"""
        path = self.get_screenshot_path(filename)
        if os.path.exists(path):
            os.remove(path)
            print(f"🗑️ 已删除: {filename}")
