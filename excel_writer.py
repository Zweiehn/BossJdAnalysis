"""Excel 写入模块 - 自动创建/追加 Excel 数据库"""

import os
import threading
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from models import JDRecord, FIELD_ORDER
from config import Config, get_app_dir


class ExcelWriter:
    """Excel 文件写入器，支持自动创建和追加"""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self._lock = threading.Lock()  # 线程安全

    def _get_excel_path(self) -> str:
        """获取 Excel 文件路径"""
        path = self.config.excel_path
        if os.path.isabs(path):
            return path
        return os.path.join(get_app_dir(), path)

    def _ensure_headers(self, ws):
        """确保表头存在（如果行为空则写入）"""
        if ws.max_row == 0 or all(ws.cell(1, c).value is None for c in range(1, len(FIELD_ORDER) + 1)):
            # 写入表头
            header_font = Font(bold=True, size=11)
            header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

            for col_idx, field_name in enumerate(FIELD_ORDER, 1):
                cell = ws.cell(1, col_idx, field_name)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_align

    # 需要限制宽度的长文本列（1-based Excel列号）
    _NARROW_COLUMNS = {
        21: 35,   # 原始JD文本 — 窄列宽，靠换行显示全文
    }

    def _auto_column_width(self, ws):
        """自动调整列宽（长文本列固定窄宽，靠自动换行）"""
        for col_idx in range(1, len(FIELD_ORDER) + 1):
            col_letter = get_column_letter(col_idx)

            # 长文本列用固定窄宽
            if col_idx in self._NARROW_COLUMNS:
                ws.column_dimensions[col_letter].width = self._NARROW_COLUMNS[col_idx]
                continue

            max_length = 0
            for row in ws.iter_rows(min_col=col_idx, max_col=col_idx, values_only=False):
                for cell in row:
                    if cell.value:
                        cell_len = 0
                        for char in str(cell.value):
                            cell_len += 2 if '一' <= char <= '鿿' else 1
                        max_length = max(max_length, cell_len)

            adjusted = min(max(max_length + 2, 8), 45)
            ws.column_dimensions[col_letter].width = adjusted

    def append_record(self, record: JDRecord):
        """
        追加一条记录到 Excel

        Args:
            record: JD记录对象
        """
        with self._lock:
            excel_path = self._get_excel_path()
            file_exists = os.path.exists(excel_path)

            if file_exists:
                try:
                    wb = load_workbook(excel_path)
                    ws = wb.active
                except PermissionError:
                    raise PermissionError(
                        f"无法写入 Excel，请先关闭文件: {excel_path}"
                    )
            else:
                wb = Workbook()
                ws = wb.active
                ws.title = "JD记录"

            # 确保表头存在
            if not file_exists:
                self._ensure_headers(ws)

            # 追加数据行
            row_data = record.to_list()
            ws.append(row_data)

            # 设置新行的对齐方式（原始JD文本列不换行，防止撑高行）
            new_row = ws.max_row
            for col_idx in range(1, len(FIELD_ORDER) + 1):
                cell = ws.cell(new_row, col_idx)
                cell.alignment = Alignment(
                    vertical="center",
                    wrap_text=(col_idx != 21)  # 21=原始JD文本，不换行
                )

            # 截图文件列设为可点击的超链接
            screenshot_cell = ws.cell(new_row, 22)
            if screenshot_cell.value:
                screenshot_cell.hyperlink = str(screenshot_cell.value)

            # 调整列宽（仅首次或隔段时间做）
            self._auto_column_width(ws)

            # 冻结首行
            ws.freeze_panes = "A2"

            # 保存
            try:
                wb.save(excel_path)
                print(f"数据已写入: {excel_path} (第{new_row - 1}条)")
            except PermissionError:
                raise PermissionError(
                    f"保存 Excel 失败，请先关闭文件: {excel_path}"
                )

    def append_records(self, records: list):
        """批量追加记录"""
        for record in records:
            self.append_record(record)

    def get_record_count(self) -> int:
        """获取当前记录数"""
        excel_path = self._get_excel_path()
        if not os.path.exists(excel_path):
            return 0
        try:
            wb = load_workbook(excel_path, read_only=True)
            ws = wb.active
            count = max(0, ws.max_row - 1)  # 减去表头
            wb.close()
            return count
        except Exception:
            return 0

    def open_excel(self):
        """打开 Excel 文件（系统默认程序）"""
        import subprocess
        excel_path = self._get_excel_path()
        if os.path.exists(excel_path):
            os.startfile(excel_path)
        else:
            raise FileNotFoundError(f"Excel 文件尚未创建: {excel_path}")
