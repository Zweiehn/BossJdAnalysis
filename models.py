"""数据模型模块 - 定义JD记录的数据结构"""

from dataclasses import dataclass, fields, asdict
from datetime import datetime


# 固定字段顺序（同时也是Excel表头顺序）
FIELD_ORDER = [
    "公司名称",
    "公司行业",
    "主营业务",
    "公司规模",
    "所在区域",
    "办公场所",
    "岗位名称",
    "薪资范围",
    "经验要求",
    "学历要求",
    "岗位关键词",
    "技术关键词",
    "是否涉及AI应用",
    "是否涉及RAG",
    "是否涉及Agent",
    "是否涉及RPA",
    "是否涉及视频生成",
    "个人匹配度",
    "优先级",
    "个人备注",
    "录入时间",
    "原始JD文本",
    "截图文件",
]


@dataclass
class JDRecord:
    """一条JD记录，字段顺序与FIELD_ORDER一致"""

    公司名称: str = ""
    公司行业: str = ""
    主营业务: str = ""
    公司规模: str = ""
    所在区域: str = ""
    办公场所: str = ""
    岗位名称: str = ""
    薪资范围: str = ""
    经验要求: str = ""
    学历要求: str = ""
    岗位关键词: str = ""  # 逗号分隔
    技术关键词: str = ""  # 逗号分隔
    是否涉及AI应用: str = "否"
    是否涉及RAG: str = "否"
    是否涉及Agent: str = "否"
    是否涉及RPA: str = "否"
    是否涉及视频生成: str = "否"
    个人匹配度: int = 5
    优先级: str = ""
    个人备注: str = ""
    录入时间: str = ""
    原始JD文本: str = ""
    截图文件: str = ""

    def to_dict(self) -> dict:
        """转为有序字典，按FIELD_ORDER排序"""
        d = asdict(self)
        return {k: d[k] for k in FIELD_ORDER}

    def to_list(self) -> list:
        """转为列表，按FIELD_ORDER顺序"""
        d = asdict(self)
        return [d.get(k, "") for k in FIELD_ORDER]

    @classmethod
    def field_names(cls) -> list:
        return FIELD_ORDER

    @classmethod
    def from_ai_response(cls, data: dict, raw_text: str = "", screenshot_file: str = "") -> "JDRecord":
        """从AI返回的dict创建记录，自动填充录入时间和原始文本"""
        record = cls()
        for key in FIELD_ORDER:
            if key in data and data[key] is not None:
                setattr(record, key, data[key])
        # 自动填充
        record.录入时间 = datetime.now().strftime("%Y-%m-%d %H:%M")
        record.原始JD文本 = raw_text
        record.截图文件 = screenshot_file
        return record
