"""简历管理模块 - 上传、分析、存储简历信息，用于JD匹配度评分"""

import os
import json
import requests
from datetime import datetime
from config import Config, get_app_dir


RESUME_FILE = "resume_profile.json"

# 简历分析 Prompt
RESUME_ANALYZE_PROMPT = """你是一个简历分析助手。请从以下简历文本中提取结构化信息，以 JSON 格式返回。

## 输出 JSON 字段定义：
{
  "姓名": "姓名（如有）",
  "最高学历": "如 本科、硕士、博士",
  "毕业院校": "毕业院校名称",
  "工作年限": "如 3年、5年",
  "当前公司": "当前/最近公司",
  "当前岗位": "当前/最近岗位名称",
  "技能清单": ["Python", "PyTorch", ...],
  "行业经验": ["互联网", "金融", ...],
  "项目亮点": "简要描述最突出的项目经验（50字内）",
  "求职意向": "如 NLP算法工程师、后端开发 等",
  "原始文本摘要": "简历原文的前200字摘要"
}

注意：如果信息在简历中未提及，用空字符串或空数组。"""


class ResumeManager:
    """简历管理器"""

    def __init__(self, config: Config = None):
        self.config = config or Config()

    def _get_profile_path(self) -> str:
        """获取简历配置文件的完整路径"""
        return os.path.join(get_app_dir(), RESUME_FILE)

    def has_resume(self) -> bool:
        """是否已有简历分析结果"""
        path = self._get_profile_path()
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data.get("技能清单")) or bool(data.get("原始文本摘要"))
        except Exception:
            return False

    def get_profile(self) -> dict:
        """获取已保存的简历分析结果"""
        path = self._get_profile_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_profile_summary(self) -> str:
        """获取简历简介（用于界面显示）"""
        profile = self.get_profile()
        if not profile:
            return "未导入简历"
        parts = []
        if profile.get("姓名"):
            parts.append(profile["姓名"])
        if profile.get("当前岗位"):
            parts.append(profile["当前岗位"])
        if profile.get("工作年限"):
            parts.append(profile["工作年限"])
        if profile.get("最高学历"):
            parts.append(profile["最高学历"])
        skills = profile.get("技能清单", [])
        if skills:
            skills_str = ", ".join(skills[:5])
            if len(skills) > 5:
                skills_str += "..."
            parts.append(f"[{skills_str}]")
        return " | ".join(parts) if parts else "简历已导入"

    def analyze_resume(self, resume_text: str, api_key: str, model: str = "deepseek-chat") -> dict:
        """
        调用 AI 分析简历，返回结构化数据

        Args:
            resume_text: 简历文本
            api_key: DeepSeek API Key
            model: 模型名称

        Returns:
            结构化简历数据字典
        """
        if not resume_text or not resume_text.strip():
            raise ValueError("简历文本为空")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": RESUME_ANALYZE_PROMPT},
                {"role": "user", "content": f"请分析以下简历：\n\n{resume_text}"},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )

        if resp.status_code != 200:
            raise RuntimeError(f"API 错误 (HTTP {resp.status_code})")

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        profile = json.loads(content)

        # 保存分析结果
        profile["_导入时间"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.save_profile(profile)

        return profile

    def save_profile(self, profile: dict):
        """保存简历分析结果到文件"""
        path = self._get_profile_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

    def clear_resume(self):
        """清除简历信息"""
        path = self._get_profile_path()
        if os.path.exists(path):
            os.remove(path)

    def build_matching_context(self) -> str:
        """
        构建用于 JD 匹配度评分的上下文文本
        返回空字符串表示无简历数据
        """
        profile = self.get_profile()
        if not profile:
            return ""

        parts = []
        parts.append(f"【我的简历信息（用于匹配度评分）】")

        if profile.get("最高学历"):
            parts.append(f"学历: {profile['最高学历']}")
        if profile.get("毕业院校"):
            parts.append(f"院校: {profile['毕业院校']}")
        if profile.get("工作年限"):
            parts.append(f"经验: {profile['工作年限']}")
        if profile.get("当前公司"):
            parts.append(f"公司: {profile['当前公司']}")
        if profile.get("当前岗位"):
            parts.append(f"岗位: {profile['当前岗位']}")

        skills = profile.get("技能清单", [])
        if skills:
            parts.append(f"技能: {', '.join(skills)}")

        industries = profile.get("行业经验", [])
        if industries:
            parts.append(f"行业: {', '.join(industries)}")

        if profile.get("项目亮点"):
            parts.append(f"项目: {profile['项目亮点']}")

        if profile.get("求职意向"):
            parts.append(f"意向: {profile['求职意向']}")

        return "\n".join(parts)
