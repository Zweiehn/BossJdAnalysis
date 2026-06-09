"""Boss直聘 JD 分析器 - 主入口 + tkinter GUI"""

import os
import sys
import threading
from datetime import datetime
from tkinter import (
    Tk, Frame, LabelFrame, Label, Button, Listbox, Text, Scrollbar,
    Entry, messagebox, filedialog, ttk, Toplevel, StringVar, Canvas,
    END, NORMAL, DISABLED, WORD, SEL, SUNKEN, X, Y, BOTH, LEFT, RIGHT, TOP, BOTTOM,
)

# 确保应用根目录在 sys.path 中
from config import get_app_dir
_app_root = get_app_dir()
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

from config import Config, get_app_dir
from models import JDRecord
from screenshot_manager import ScreenshotManager
from excel_writer import ExcelWriter
from ocr.paddle_ocr_impl import PaddleOCREngine
from ai.deepseek_impl import DeepSeekAI
from feishu_sync import FeishuSyncer


class JDAnalyzerApp:
    """主应用窗口"""

    def __init__(self, root: Tk):
        self.root = root
        self.root.title("Boss直聘 JD 分析器")
        self.root.geometry("880x620")
        self.root.minsize(700, 500)

        # 初始化核心模块
        self.config = Config()
        self.screenshot_mgr = ScreenshotManager(self.config)
        self.excel_writer = ExcelWriter(self.config)

        # OCR 引擎 (延迟初始化)
        self.ocr_engine = None

        # 待处理队列
        self.file_queue = []  # [(原始路径, 显示名), ...]
        self.is_processing = False

        # 设置 UI
        self._setup_ui()

        # 检查 API Key
        self._check_api_key()

    # ──────────────── UI 布局 ────────────────

    def _setup_ui(self):
        """构建界面"""
        # ── 顶部工具栏 ──
        toolbar = Frame(self.root, padx=10, pady=8)
        toolbar.pack(fill=X)

        self.btn_select = Button(
            toolbar, text="📁 选择截图", command=self._select_files,
            width=12, height=1, font=("微软雅黑", 10),
        )
        self.btn_select.pack(side=LEFT, padx=2)

        self.btn_process = Button(
            toolbar, text="▶ 批量处理", command=self._start_batch_process,
            width=12, height=1, font=("微软雅黑", 10),
            state=DISABLED,
        )
        self.btn_process.pack(side=LEFT, padx=2)

        self.btn_open_excel = Button(
            toolbar, text="📊 打开Excel", command=self._open_excel,
            width=12, height=1, font=("微软雅黑", 10),
        )
        self.btn_open_excel.pack(side=LEFT, padx=2)

        self.btn_screenshots = Button(
            toolbar, text="🖼 截图库", command=self._open_screenshots_folder,
            width=10, height=1, font=("微软雅黑", 10),
        )
        self.btn_screenshots.pack(side=LEFT, padx=2)

        self.btn_choose_excel = Button(
            toolbar, text="📂 导出文件", command=self._choose_excel_path,
            width=10, height=1, font=("微软雅黑", 10),
        )
        self.btn_choose_excel.pack(side=LEFT, padx=2)

        self.btn_feishu = Button(
            toolbar, text="☁ 同步飞书", command=self._sync_to_feishu,
            width=10, height=1, font=("微软雅黑", 10),
        )
        self.btn_feishu.pack(side=LEFT, padx=2)

        self.btn_config = Button(
            toolbar, text="⚙ 配置", command=self._open_config_window,
            width=8, height=1, font=("微软雅黑", 10),
        )
        self.btn_config.pack(side=RIGHT, padx=2)

        # 记录数标签
        self.lbl_count = Label(toolbar, text="记录: 0", font=("微软雅黑", 9), fg="gray")
        self.lbl_count.pack(side=RIGHT, padx=8)

        # ── 状态栏 ──
        status_frame = Frame(self.root, padx=10, pady=2)
        status_frame.pack(fill=X)

        self.lbl_status = Label(
            status_frame, text="就绪 — 点击「选择截图」开始",
            font=("微软雅黑", 9), anchor="w", fg="#555",
        )
        self.lbl_status.pack(fill=X)

        # 当前导出路径显示
        self.lbl_excel_path = Label(
            status_frame,
            text=f"📎 {self._get_display_excel_path()}",
            font=("微软雅黑", 8), anchor="w", fg="#888",
        )
        self.lbl_excel_path.pack(fill=X)

        # ── 文件列表 ──
        list_frame = Frame(self.root, padx=10, pady=4)
        list_frame.pack(fill=BOTH, expand=True)

        Label(list_frame, text="待处理文件列表:", font=("微软雅黑", 9, "bold")).pack(anchor="w")

        # 列表 + 滚动条
        list_bg_frame = Frame(list_frame)
        list_bg_frame.pack(fill=BOTH, expand=True)

        scrollbar = Scrollbar(list_bg_frame, orient="vertical")
        self.file_listbox = Listbox(
            list_bg_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            selectmode="extended",
            bg="#fafafa",
            height=8,
        )
        scrollbar.config(command=self.file_listbox.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.file_listbox.pack(side=LEFT, fill=BOTH, expand=True)

        # 列表下方操作按钮
        list_actions = Frame(list_frame, pady=4)
        list_actions.pack(fill=X)

        self.btn_remove = Button(
            list_actions, text="移除选中", command=self._remove_selected,
            state=DISABLED, font=("微软雅黑", 9),
        )
        self.btn_remove.pack(side=LEFT, padx=2)

        self.btn_clear = Button(
            list_actions, text="清空列表", command=self._clear_list,
            state=DISABLED, font=("微软雅黑", 9),
        )
        self.btn_clear.pack(side=LEFT, padx=2)

        # ── 日志 / 输出区域 ──
        log_frame = Frame(self.root, padx=10, pady=4)
        log_frame.pack(fill=BOTH, expand=True)

        Label(log_frame, text="处理日志:", font=("微软雅黑", 9, "bold")).pack(anchor="w")

        log_bg = Frame(log_frame)
        log_bg.pack(fill=BOTH, expand=True)

        log_scroll = Scrollbar(log_bg, orient="vertical")
        self.log_text = Text(
            log_bg,
            yscrollcommand=log_scroll.set,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            wrap=WORD,
            height=10,
            relief=SUNKEN,
            borderwidth=1,
        )
        log_scroll.config(command=self.log_text.yview)
        log_scroll.pack(side=RIGHT, fill=Y)
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)
        self.log_text.config(state=DISABLED)

        # ── 底部进度条 ──
        progress_frame = Frame(self.root, padx=10, pady=8)
        progress_frame.pack(fill=X)

        self.progress = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress.pack(fill=X)

        # 更新记录数
        self._update_record_count()

    # ──────────────── 方法 ────────────────

    def _check_api_key(self):
        """首次检查 API Key"""
        if not self.config.deepseek_api_key:
            self.log("⚠️ DeepSeek API Key 未配置，请点击「配置」按钮设置")
            messagebox.showwarning("API Key 未配置", "请先配置 DeepSeek API Key 才能使用 AI 分析功能。")

    def _update_record_count(self):
        """更新 Excel 记录数显示"""
        try:
            count = self.excel_writer.get_record_count()
            self.lbl_count.config(text=f"记录: {count}")
        except Exception:
            pass

    def log(self, message: str):
        """在日志区域输出消息"""
        def _append():
            self.log_text.config(state=NORMAL)
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(END, f"[{timestamp}] {message}\n")
            self.log_text.see(END)
            self.log_text.config(state=DISABLED)
        self.root.after(0, _append)

    def _update_file_list_ui(self):
        """更新文件列表 UI 状态"""
        count = self.file_listbox.size()
        self.btn_process.config(state=NORMAL if count > 0 and not self.is_processing else DISABLED)
        self.btn_remove.config(state=NORMAL if count > 0 else DISABLED)
        self.btn_clear.config(state=NORMAL if count > 0 else DISABLED)

    def _refresh_file_list(self):
        """刷新文件列表显示"""
        self.file_listbox.delete(0, END)
        for orig_path, display_name in self.file_queue:
            self.file_listbox.insert(END, f"  {display_name}")
        self._update_file_list_ui()

    # ──────────────── 事件处理 ────────────────

    def _select_files(self):
        """选择截图文件"""
        files = filedialog.askopenfiles(
            title="选择 Boss直聘 截图",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg"),
                ("所有文件", "*.*"),
            ],
        )
        if not files:
            return

        added = 0
        for f in files:
            path = f.name
            # 检查是否已在队列中
            if any(path == orig for orig, _ in self.file_queue):
                continue
            display_name = os.path.basename(path)
            self.file_queue.append((path, display_name))
            added += 1

        if added > 0:
            self._refresh_file_list()
            self.log(f"📁 已添加 {added} 个文件")
            self.lbl_status.config(text=f"已选 {len(self.file_queue)} 个文件，点击「批量处理」开始")
        else:
            self.log("ℹ️ 没有新文件需要添加")

    def _remove_selected(self):
        """移除选中的文件"""
        selected = self.file_listbox.curselection()
        if not selected:
            return
        # 从后往前删，避免索引变化
        for idx in reversed(selected):
            del self.file_queue[idx]
        self._refresh_file_list()
        self.log(f"🗑️ 已移除 {len(selected)} 个文件")

    def _clear_list(self):
        """清空队列"""
        if not self.file_queue:
            return
        if messagebox.askyesno("确认", "确定清空所有待处理文件？"):
            self.file_queue.clear()
            self._refresh_file_list()
            self.log("🗑️ 已清空文件列表")

    def _open_excel(self):
        """打开 Excel 文件"""
        try:
            self.excel_writer.open_excel()
            self.log("📊 已打开 Excel 文件")
        except FileNotFoundError as e:
            messagebox.showinfo("提示", "Excel 文件尚未创建，请先处理至少一条记录。")
        except Exception as e:
            messagebox.showerror("错误", f"打开 Excel 失败: {e}")

    def _open_screenshots_folder(self):
        """打开截图库文件夹"""
        ss_dir = self.screenshot_mgr.get_screenshot_dir()
        if os.path.exists(ss_dir):
            os.startfile(ss_dir)
            self.log(f"🖼 已打开截图库: {ss_dir}")
        else:
            os.makedirs(ss_dir, exist_ok=True)
            os.startfile(ss_dir)
            self.log(f"🖼 已创建并打开截图库: {ss_dir}")

    def _get_display_excel_path(self) -> str:
        """获取用于界面显示的Excel路径简写"""
        raw = self.config.excel_path
        if os.path.isabs(raw):
            return raw
        return os.path.join(get_app_dir(), raw)

    def _choose_excel_path(self):
        """选择导出Excel文件的路径（选定后持久化，不可回退）"""
        path = filedialog.asksaveasfilename(
            title="选择导出Excel文件",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")],
        )
        if not path:
            return

        # 保存到配置（覆盖旧值）
        self.config.set("excel_path", path)

        # 重建 excel_writer 使用新路径
        self.excel_writer = ExcelWriter(self.config)

        # 更新界面
        self.lbl_excel_path.config(text=f"📎 {path}")
        self._update_record_count()
        self.log(f"📂 导出文件已切换至: {path}")

    # ──────────────── 飞书同步 ────────────────

    def _sync_to_feishu(self):
        """同步 Excel 数据到飞书多维表格"""
        syncer = FeishuSyncer(self.config)

        if not syncer.is_configured():
            msg = syncer.check_config()
            self.log(f"☁ 飞书未配置: {msg}，请先在「配置」中填写")
            messagebox.showwarning("飞书未配置",
                f"飞书配置不完整：{msg}\n\n"
                "请先在「配置」中填写飞书信息：\n"
                "1. App ID / App Secret（从开放平台获取）\n"
                "2. Base Token（多维表格URL中的ID）\n"
                "3. Table ID（表格页面URL中获取）")
            return

        # 确认同步
        if not messagebox.askyesno("同步确认",
            "确定将 Excel 数据同步到飞书多维表格？\n\n"
            "• 现有的飞书表格数据不会被清除\n"
            "• 新增的记录会追加到表格末尾\n"
            "• 请确保飞书表格表头与 Excel 一致"):
            return

        self.log("☁ 正在同步到飞书...")
        self.lbl_status.config(text="☁ 同步到飞书中...")

        def _do_sync():
            try:
                result = syncer.sync_excel_to_bitable()
                self.root.after(0, lambda: self._on_sync_done(result))
            except Exception as e:
                self.root.after(0, lambda: self._on_sync_error(str(e)))

        thread = threading.Thread(target=_do_sync, daemon=True)
        thread.start()

    def _test_feishu_connection(self, entry_fs_appid=None, entry_fs_secret=None,
                                 entry_fs_base=None, entry_fs_table=None):
        """测试飞书连接权限（优先从界面输入框取值）"""
        app_id = entry_fs_appid.get().strip() if entry_fs_appid else self.config.feishu_app_id
        secret = entry_fs_secret.get().strip() if entry_fs_secret else self.config.feishu_app_secret
        base_token = entry_fs_base.get().strip() if entry_fs_base else self.config.feishu_base_token
        table_id = entry_fs_table.get().strip() if entry_fs_table else self.config.feishu_table_id

        if not all([app_id, secret, base_token, table_id]):
            messagebox.showwarning("飞书未配置", "请先填写完整的飞书配置信息")
            return

        # 创建临时配置
        from config import Config
        tmp_cfg = Config()
        tmp_cfg.set("feishu_app_id", app_id)
        tmp_cfg.set("feishu_app_secret", secret)
        tmp_cfg.set("feishu_base_token", base_token)
        tmp_cfg.set("feishu_table_id", table_id)

        syncer = FeishuSyncer(tmp_cfg)
        result = syncer.test_connection()
        if not result:
            messagebox.showinfo("连接成功", "飞书连接正常，可以同步数据！")
        else:
            messagebox.showerror("连接失败", result)

    def _on_sync_done(self, result: dict):
        """同步完成回调"""
        if result.get("failed", 0) > 0:
            info = result.get("info", "")
            self.log(f"☁ {info}")
            for err in result.get("errors", [])[:3]:
                for line in err[1].split("\n"):
                    self.log(f"  {line}")
            # 如果有详细指引，弹出完整信息
            first_err = result["errors"][0][1] if result["errors"] else info
            messagebox.showerror("同步失败", first_err)
        else:
            self.log(f"☁ {result.get('info', '同步完成')}")
            messagebox.showinfo("同步成功", result.get("info", "同步完成"))
        self.lbl_status.config(text="就绪")

    def _on_sync_error(self, error: str):
        """同步失败回调"""
        self.log(f"☁ 同步失败: {error}")
        self.lbl_status.config(text="同步失败")
        messagebox.showerror("同步失败", error)

    # ──────────────── 配置窗口 ────────────────

    def _open_config_window(self):
        """打开配置对话框（可滚动）"""
        win = Toplevel(self.root)
        win.title("配置")
        win.geometry("580x520")
        win.minsize(560, 400)
        win.resizable(True, True)
        win.transient(self.root)
        win.grab_set()

        # ── 可滚动容器 ──
        canvas = Canvas(win, highlightthickness=0)
        scrollbar = Scrollbar(win, orient="vertical", command=canvas.yview)
        scroll_frame = Frame(canvas, padx=10, pady=5)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # 鼠标滚轮支持
        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        win.protocol("WM_DELETE_WINDOW", lambda: (canvas.unbind_all("<MouseWheel>"), win.destroy()))

        # ── DeepSeek 配置 ──
        frame_ds = LabelFrame(scroll_frame, text="DeepSeek AI 配置", font=("微软雅黑", 9, "bold"), padx=10, pady=5)
        frame_ds.pack(fill=X, pady=(5, 3))

        Label(frame_ds, text="API Key:", font=("微软雅黑", 9)).pack(anchor="w", pady=(5, 2))
        entry_key = Entry(frame_ds, font=("Consolas", 10), show="*")
        entry_key.pack(fill=X)
        entry_key.insert(0, self.config.deepseek_api_key)
        Label(frame_ds, text="从 platform.deepseek.com 获取", font=("微软雅黑", 8), fg="gray").pack(anchor="w")

        Label(frame_ds, text="模型名称:", font=("微软雅黑", 9)).pack(anchor="w", pady=(8, 2))
        entry_model = Entry(frame_ds, font=("Consolas", 10))
        entry_model.pack(fill=X)
        entry_model.insert(0, self.config.deepseek_model)

        Label(frame_ds, text="AI 温度 (0-1, 越低越稳定):", font=("微软雅黑", 9)).pack(anchor="w", pady=(8, 2))
        entry_temp = Entry(frame_ds, font=("Consolas", 10), width=10)
        entry_temp.pack(anchor="w")
        entry_temp.insert(0, str(self.config.ai_temperature))

        # ── 飞书配置 ──
        frame_fs = LabelFrame(scroll_frame, text="飞书多维表格 配置", font=("微软雅黑", 9, "bold"), padx=10, pady=5)
        frame_fs.pack(fill=X, pady=3)

        Label(frame_fs, text="App ID:", font=("微软雅黑", 9)).pack(anchor="w", pady=(5, 2))
        entry_fs_appid = Entry(frame_fs, font=("Consolas", 10))
        entry_fs_appid.pack(fill=X)
        entry_fs_appid.insert(0, self.config.feishu_app_id)

        Label(frame_fs, text="App Secret:", font=("微软雅黑", 9)).pack(anchor="w", pady=(8, 2))
        entry_fs_secret = Entry(frame_fs, font=("Consolas", 10), show="*")
        entry_fs_secret.pack(fill=X)
        entry_fs_secret.insert(0, self.config.feishu_app_secret)

        Label(frame_fs, text="Base Token（URL 中 /base/ 后的ID）:", font=("微软雅黑", 9)).pack(anchor="w", pady=(8, 2))
        entry_fs_base = Entry(frame_fs, font=("Consolas", 10))
        entry_fs_base.pack(fill=X)
        entry_fs_base.insert(0, self.config.feishu_base_token)

        Label(frame_fs, text="Table ID:", font=("微软雅黑", 9)).pack(anchor="w", pady=(8, 2))
        entry_fs_table = Entry(frame_fs, font=("Consolas", 10))
        entry_fs_table.pack(fill=X)
        entry_fs_table.insert(0, self.config.feishu_table_id)

        # ── 飞书接入说明 ──
        tips = LabelFrame(scroll_frame, text="飞书接入说明", font=("微软雅黑", 8, "bold"), padx=10, pady=5)
        tips.pack(fill=X, pady=3)
        tip_text = Text(tips, font=("微软雅黑", 8), height=6, wrap=WORD, fg="#555",
                        relief="flat", bg=tips.cget("bg"))
        tip_text.pack(fill=X)
        tip_text.insert(END, "1. 打开 https://open.feishu.cn 创建企业自建应用\n")
        tip_text.insert(END, "2. 开通权限: bitable:app（多维表格）\n")
        tip_text.insert(END, "3. 发布应用后获取 App ID / Secret\n")
        tip_text.insert(END, "4. 在飞书中创建多维表格\n")
        tip_text.insert(END, "5. 表头字段名与 Excel 保持一致\n")
        tip_text.insert(END, "6. 从URL获取: /base/BASE_TOKEN/?table=TABLE_ID")
        tip_text.config(state=DISABLED)

        # ── 文件路径 ──
        frame_path = LabelFrame(scroll_frame, text="文件路径", font=("微软雅黑", 9, "bold"), padx=10, pady=5)
        frame_path.pack(fill=X, pady=3)

        Label(frame_path, text="截图保存目录:", font=("微软雅黑", 9)).pack(anchor="w", pady=(5, 2))
        entry_ssdir = Entry(frame_path, font=("Consolas", 10))
        entry_ssdir.pack(fill=X)
        entry_ssdir.insert(0, self.config.screenshot_dir)

        # ── 保存按钮 ──
        def save_config():
            # DeepSeek
            self.config.set("deepseek_api_key", entry_key.get().strip())
            self.config.set("deepseek_model", entry_model.get().strip() or "deepseek-chat")
            try:
                temp = float(entry_temp.get().strip() or "0.1")
                temp = max(0.0, min(1.0, temp))
            except ValueError:
                temp = 0.1
            self.config.set("ai_temperature", temp)

            # 飞书
            self.config.set("feishu_app_id", entry_fs_appid.get().strip())
            self.config.set("feishu_app_secret", entry_fs_secret.get().strip())
            self.config.set("feishu_base_token", entry_fs_base.get().strip())
            self.config.set("feishu_table_id", entry_fs_table.get().strip())

            # 截图目录
            self.config.set("screenshot_dir", entry_ssdir.get().strip() or "screenshots")

            self.log("⚙ 配置已保存")
            canvas.unbind_all("<MouseWheel>")
            win.destroy()
            self.root.after(100, lambda: messagebox.showinfo("完成", "配置已保存！"))

        # ── 按钮行 ──
        btn_frame = Frame(scroll_frame)
        btn_frame.pack(fill=X, pady=12)
        Button(btn_frame, text="🔗 测试飞书连接",
               command=lambda: self._test_feishu_connection(
                   entry_fs_appid, entry_fs_secret, entry_fs_base, entry_fs_table),
               font=("微软雅黑", 9), width=16).pack(side=LEFT, padx=5)
        Button(btn_frame, text="💾 保存", command=save_config,
               font=("微软雅黑", 10), width=12, bg="#4a90d9", fg="white").pack(side=LEFT, padx=5)

    # ──────────────── 核心处理流程 ────────────────

    def _start_batch_process(self):
        """启动批量处理（在后台线程）"""
        if self.is_processing or not self.file_queue:
            return

        # 检查 API Key
        if not self.config.deepseek_api_key:
            messagebox.showerror("错误", "请先在配置中填写 DeepSeek API Key")
            return

        self.is_processing = True
        self.btn_process.config(state=DISABLED, text="⏳ 处理中...")
        self.btn_select.config(state=DISABLED)
        self.progress["maximum"] = len(self.file_queue)
        self.progress["value"] = 0

        # 复制队列（避免处理过程中被修改）
        queue_copy = list(self.file_queue)

        self.log(f"🚀 开始批量处理 {len(queue_copy)} 个文件...")

        # 后台线程
        thread = threading.Thread(target=self._process_queue, args=(queue_copy,), daemon=True)
        thread.start()

    def _process_queue(self, queue: list):
        """处理队列（在后台线程运行）"""
        success_count = 0
        fail_count = 0

        for idx, (file_path, display_name) in enumerate(queue):
            self.root.after(0, lambda i=idx+1: self.progress.config(value=i))
            self.root.after(0, lambda n=display_name: self.lbl_status.config(
                text=f"正在处理: {n} ({idx+1}/{len(queue)})"
            ))

            self.log(f"\n{'='*50}")
            self.log(f"📄 [{idx+1}/{len(queue)}] 处理: {display_name}")

            try:
                self._process_single(file_path, display_name)
                success_count += 1
                self.log(f"✅ [{display_name}] 处理完成")

                # 更新列表状态
                def _mark_done(n=display_name):
                    # 在文件名后加 ✓ 标记
                    items = self.file_listbox.get(0, END)
                    for i, item in enumerate(items):
                        if n in item and "✓" not in item:
                            self.file_listbox.delete(i)
                            self.file_listbox.insert(i, f"  ✅ {n}")
                            break
                self.root.after(0, _mark_done)

            except Exception as e:
                fail_count += 1
                error_msg = str(e)
                self.log(f"❌ [{display_name}] 失败: {error_msg}")

                # 标记失败
                def _mark_fail(n=display_name):
                    items = self.file_listbox.get(0, END)
                    for i, item in enumerate(items):
                        if n in item and "❌" not in item and "✅" not in item:
                            self.file_listbox.delete(i)
                            self.file_listbox.insert(i, f"  ❌ {n}")
                            break
                self.root.after(0, _mark_fail)

            self.root.after(0, lambda: self.progress.step(1))

        # 处理完成
        self._finish_processing(success_count, fail_count, queue)

    def _process_single(self, file_path: str, display_name: str):
        """处理单个文件"""
        # 1. 保存截图
        self.log("  📸 正在保存截图...")
        saved_path = self.screenshot_mgr.save_screenshot(file_path)

        # 2. OCR 识别
        self.log("  🔍 OCR 识别中...")
        if self.ocr_engine is None:
            self.ocr_engine = PaddleOCREngine(lang=self.config.ocr_lang)
            self.log(f"  🤖 OCR 引擎: {self.ocr_engine.get_name()}")

        raw_text = self.ocr_engine.extract_text(saved_path)

        if not raw_text.strip():
            raise RuntimeError("OCR 未能提取到文本内容，请检查图片质量")

        # 截取日志显示的前200字
        preview = raw_text[:200].replace("\n", " ")
        self.log(f"  📝 OCR 提取文本 ({len(raw_text)} 字): {preview}...")

        # 3. AI 分析
        self.log(f"  🤖 AI 分析中 ({self.config.deepseek_model})...")
        ai = DeepSeekAI(
            api_key=self.config.deepseek_api_key,
            model=self.config.deepseek_model,
            temperature=self.config.ai_temperature,
            max_retries=self.config.ai_max_retries,
        )

        ai_result = ai.analyze_jd(raw_text)
        self.log(f"  📊 AI 分析完成: {ai_result.get('公司名称', '?')} — {ai_result.get('岗位名称', '?')}")

        # 4. 写入 Excel
        self.log("  💾 写入 Excel...")
        record = JDRecord.from_ai_response(ai_result, raw_text, saved_path)
        self.excel_writer.append_record(record)

        # 显示摘要
        self.log(f"  🏢 公司: {record.公司名称}")
        self.log(f"  💼 岗位: {record.岗位名称} | {record.薪资范围} | {record.经验要求}/{record.学历要求}")
        self.log(f"  📍 区域: {record.所在区域}")

    def _finish_processing(self, success: int, fail: int, queue: list):
        """处理完成后的收尾工作"""
        def _done():
            self.is_processing = False
            self.btn_process.config(state=NORMAL, text="▶ 批量处理")
            self.btn_select.config(state=NORMAL)

            # 从队列中移除已处理完成的文件
            remaining = []
            for orig_path, display_name in queue:
                if not any(display_name == d for _, d in self.file_queue):
                    continue
                # 检查是否标记为成功或失败
                items = self.file_listbox.get(0, END)
                is_done = any((display_name in item and ("✅" in item or "❌" in item)) for item in items)
                if not is_done:
                    remaining.append((orig_path, display_name))

            self.file_queue.clear()
            self.file_queue.extend(remaining)
            self._refresh_file_list()

            # 更新记录数
            self._update_record_count()

            summary = f"处理完成: 成功 {success}, 失败 {fail}"
            self.lbl_status.config(text=summary)

            if fail == 0:
                self.log(f"\n🎉 全部处理完成！共 {success} 条记录已写入 Excel")
                messagebox.showinfo("完成", f"成功处理 {success} 条记录！\n\nExcel 文件: {self.config.excel_path}")
            else:
                self.log(f"\n⚠️ 处理完成: 成功 {success}, 失败 {fail}")
                if success > 0:
                    messagebox.showwarning("部分完成", f"成功: {success}\n失败: {fail}\n\n请检查失败的图片。")

        self.root.after(0, _done)


def main():
    """程序入口"""
    root = Tk()
    root.tk.call("encoding", "system", "utf-8")  # 支持中文
    app = JDAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
