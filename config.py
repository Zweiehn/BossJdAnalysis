"""配置管理模块 - 读取/写入 config.json"""

import json
import os
import sys


def get_app_dir() -> str:
    """
    获取应用程序根目录（兼容 PyInstaller 打包）
    - 脚本模式: 返回 config.py 所在目录
    - exe 模式: 返回 exe 所在目录
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# 默认配置
DEFAULT_CONFIG = {
    "deepseek_api_key": "",
    "deepseek_model": "deepseek-chat",
    "ai_temperature": 0.1,
    "ai_max_retries": 2,
    "screenshot_dir": "screenshots",
    "excel_path": "boss_jd_records.xlsx",
    "ocr_lang": "ch",
}


class Config:
    """配置管理器，单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if self._loaded:
            return
        self._loaded = True
        self.config_path = self._find_config_path()
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def _find_config_path(self) -> str:
        """获取 config.json 路径（在应用根目录下）"""
        return os.path.join(get_app_dir(), "config.json")

    def load(self):
        """从文件加载配置，缺失字段用默认值"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                for k, v in loaded.items():
                    self.data[k] = v
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ 配置文件读取失败，使用默认配置: {e}")
        else:
            self.save()

    def save(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except IOError as e:
            print(f"⚠️ 配置保存失败: {e}")

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value):
        self.data[key] = value
        self.save()

    @property
    def deepseek_api_key(self) -> str:
        return self.data.get("deepseek_api_key", "")

    @property
    def deepseek_model(self) -> str:
        return self.data.get("deepseek_model", "deepseek-chat")

    @property
    def ai_temperature(self) -> float:
        return float(self.data.get("ai_temperature", 0.1))

    @property
    def ai_max_retries(self) -> int:
        return int(self.data.get("ai_max_retries", 2))

    @property
    def screenshot_dir(self) -> str:
        return self.data.get("screenshot_dir", "screenshots")

    @property
    def excel_path(self) -> str:
        return self.data.get("excel_path", "boss_jd_records.xlsx")

    @property
    def ocr_lang(self) -> str:
        return self.data.get("ocr_lang", "ch")

    @property
    def feishu_app_id(self) -> str:
        return self.data.get("feishu_app_id", "")

    @property
    def feishu_app_secret(self) -> str:
        return self.data.get("feishu_app_secret", "")

    @property
    def feishu_base_token(self) -> str:
        return self.data.get("feishu_base_token", "")

    @property
    def feishu_table_id(self) -> str:
        return self.data.get("feishu_table_id", "")

    def resolve_excel_path(self) -> str:
        """获取 Excel 文件的完整绝对路径"""
        path = self.excel_path
        if os.path.isabs(path):
            return path
        return os.path.join(get_app_dir(), path)
