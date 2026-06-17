# Boss直聘 JD 分析器

从 Boss直聘 长截图中自动提取招聘信息，通过 OCR + AI 分析写入本地 Excel，支持同步飞书多维表格。

## 功能

- 📸 **截图管理** — 自动保存并命名截图 `boss_jd_YYYYMMDD_NNN.png`
- 🔍 **OCR 识别** — PaddleOCR 引擎，支持中文长图
- 🤖 **AI 分析** — DeepSeek API 提取 22 个结构化字段
- 📊 **Excel 数据库** — 自动创建/追加，固定字段顺序，超链接跳转原图
- ☁ **飞书同步** — 一键同步到飞书多维表格，内置去重
- 🖼 **截图库** — 一键打开截图文件夹，方便溯源

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制配置文件并填入 API Key：

```bash
cp config.example.json config.json
```

编辑 `config.json`，填入 DeepSeek API Key（从 [platform.deepseek.com](https://platform.deepseek.com) 获取）

### 3. 运行

```bash
python main.py
```

### 4. 打包 exe

```bash
pip install pyinstaller
pyinstaller --onedir --name "BossJD分析器" --noconsole --add-data "config.json;." --add-data "ocr;ocr" --add-data "ai;ai" --hidden-import "paddleocr" --hidden-import "paddle" --hidden-import "skimage" --hidden-import "imgaug" --hidden-import "lmdb" --hidden-import "pyclipper" --hidden-import "shapely" --collect-all "paddleocr" main.py
```

## 飞书同步配置

1. 在 [open.feishu.cn](https://open.feishu.cn) 创建企业自建应用
2. 开通 `bitable:app` 权限
3. 发布应用，获取 App ID / App Secret
4. 创建多维表格，表头与 Excel 字段一致
5. 在工具「配置」中填写飞书信息

## 项目结构

```
boss_jd_analyzer/
├── main.py                 # 主入口 + tkinter GUI
├── config.py               # 配置管理
├── models.py               # 数据模型 (22个字段)
├── screenshot_manager.py   # 截图文件管理
├── excel_writer.py         # Excel 读写
├── feishu_sync.py          # 飞书多维表格同步
├── ocr/
│   ├── base.py             # OCR 抽象基类
│   └── paddle_ocr_impl.py  # PaddleOCR 实现
├── ai/
│   ├── base.py             # AI 分析抽象基类
│   └── deepseek_impl.py    # DeepSeek API 实现
├── config.example.json     # 配置模板
├── requirements.txt        # Python 依赖
├── .gitignore
└── README.md
```

## 导出字段

公司名称、公司行业、主营业务、公司规模、所在区域、办公场所、岗位名称、薪资范围、经验要求、学历要求、岗位关键词、技术关键词、是否涉及AI应用、是否涉及RAG、是否涉及Agent、是否涉及RPA、是否涉及视频生成、个人匹配度、个人备注、录入时间、原始JD文本、截图文件

第一次打开exe之前先运行：
pip install paddlepaddle paddleocr
