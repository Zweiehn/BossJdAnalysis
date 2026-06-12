"""DeepSeek API 实现 - 通过 OpenAI 兼容接口调用 DeepSeek"""

import json
import time
import requests
from .base import BaseAI


# System Prompt - 精确定义提取规则和 JSON 输出格式
SYSTEM_PROMPT = """你是一个招聘信息分析助手。从以下招聘JD文本中提取结构化信息，以 JSON 格式返回。

## 输出 JSON 字段定义：
{
  "公司名称": "公司全称",
  "公司行业": "公司所属行业",
  "主营业务": "公司主要业务描述",
  "公司规模": "如 100-499人、500-2000人、2000人以上 等",
  "所在区域": "工作地点，如 北京市海淀区、上海浦东新区、深圳南山区 等",
  "办公场所": "具体办公地点，如 某某工业园、某某写字楼、某某大厦 等",
  "岗位名称": "职位名称",
  "薪资范围": "保持原文薪资格式，如 25K-50K、15k-25k·15薪 等",
  "经验要求": "如 3-5年、5-10年、不限 等",
  "学历要求": "如 本科、硕士、大专、不限 等",
  "岗位关键词": "提取3-8个岗位核心关键词，英文逗号分隔",
  "技术关键词": "提取JD中提到的技术栈关键词，英文逗号分隔，如 Python,PyTorch,Redis",
  "是否涉及AI应用": "是 或 否",
  "是否涉及RAG": "是 或 否",
  "是否涉及Agent": "是 或 否",
  "是否涉及RPA": "是 或 否",
  "是否涉及视频生成": "是 或 否",
  "个人匹配度": "1-10的整数，根据JD要求与你的知识综合评估",
  "个人备注": "对该岗位的简要观察、建议或注意事项"
}

## 提取规则：
1. 如果某个字段在原文中未提及，使用空字符串
2. 薪资范围保持原文格式不变
3. 技术关键词只提取具体的技术/工具名称，不要写描述性文字
4. 是否类字段严格返回 "是" 或 "否"
5. 个人匹配度必须是1-10的整数
6. 确保 JSON 格式合法，可以被 json.loads() 直接解析"""


class DeepSeekAI(BaseAI):
    """DeepSeek API 封装"""

    def __init__(self, api_key: str, model: str = "deepseek-chat",
                 temperature: float = 0.1, max_retries: int = 2):
        """
        Args:
            api_key: DeepSeek API Key
            model: 模型名，默认 deepseek-chat
            temperature: 生成温度，默认 0.1（保证一致性）
            max_retries: 失败重试次数
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.base_url = "https://api.deepseek.com/v1/chat/completions"

    def _build_messages(self, raw_text: str, resume_context: str = "") -> list:
        """构建消息列表，如有简历数据则用于匹配度评分"""
        system = SYSTEM_PROMPT
        if resume_context:
            system += f"\n\n{resume_context}\n\n## 匹配度评分要求：\n请将上面的「我的简历信息」与当前JD进行对比，按以下标准给出「个人匹配度」：\n- 9-10：JD要求与简历高度匹配（技能、经验、学历都吻合）\n- 7-8：大部分匹配，少量差距\n- 5-6：部分匹配，有可迁移经验\n- 3-4：少量匹配，需要较大转型\n- 1-2：基本不匹配\n在「个人备注」中简要说明评分理由。"

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": f"请分析以下招聘JD文本，提取结构化信息：\n\n{raw_text}"},
        ]

    def analyze_jd(self, raw_text: str, resume_context: str = "") -> dict:
        """
        分析JD文本，返回结构化JSON数据

        Args:
            raw_text: OCR 提取的原始文本
            resume_context: 简历上下文（用于匹配度评分），空字符串则不使用

        Returns:
            结构化数据字典
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("JD 文本为空，无法分析")

        if not self.api_key:
            raise RuntimeError("DeepSeek API Key 未配置，请在设置中填写")

        # 构建请求
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": self._build_messages(raw_text, resume_context),
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }

        # 带重试的请求
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    wait = attempt * 2
                    print(f"  重试 {attempt}/{self.max_retries} (等待 {wait}s)...")
                    time.sleep(wait)

                resp = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=60,
                )

                if resp.status_code == 401:
                    raise RuntimeError("API Key 无效，请在设置中检查")
                elif resp.status_code == 429:
                    raise RuntimeError("请求过于频繁，请稍后重试")
                elif resp.status_code != 200:
                    raise RuntimeError(
                        f"API 返回错误 (HTTP {resp.status_code}): {resp.text[:200]}"
                    )

                data = resp.json()
                content = data["choices"][0]["message"]["content"]

                # 解析 JSON
                parsed = json.loads(content)

                # 验证必要字段
                if not isinstance(parsed, dict):
                    raise ValueError("API 返回的不是 JSON 对象")

                return parsed

            except json.JSONDecodeError as e:
                last_error = ValueError(f"JSON 解析失败: {e}")
            except requests.exceptions.Timeout:
                last_error = RuntimeError("API 请求超时")
            except requests.exceptions.ConnectionError:
                last_error = RuntimeError("API 连接失败，请检查网络")
            except RuntimeError as e:
                last_error = e
                if attempt < self.max_retries:
                    continue  # 只有 RuntimeError 才重试
                break
            except Exception as e:
                last_error = RuntimeError(f"未知错误: {e}")
                break

        raise last_error or RuntimeError("AI 分析失败")

    def get_name(self) -> str:
        return f"DeepSeek ({self.model})"
