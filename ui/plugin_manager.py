"""插件管理界面：列出 / 安装 / 启用 / 禁用 / 卸载，并按分类筛选。

这是微内核的基础设施（管理插件本身），不是业务插件：它不向任何扩展点贡献内容。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.errors import KernelError
from core.kernel import OperationResult

ALL_CATEGORIES = "__all__"


class PluginManagerDialog(QDialog):
    def __init__(self, kernel, parent=None):
        super().__init__(parent)
        self.kernel = kernel
        self.setWindowTitle("插件管理")
        self.resize(900, 580)

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("分类筛选："))
        self._filter = QComboBox(self)
        self._filter.currentIndexChanged.connect(lambda _: self._refresh())
        top.addWidget(self._filter, 1)
        refresh_button = QPushButton("刷新", self)
        refresh_button.clicked.connect(self._refresh)
        top.addWidget(refresh_button)
        layout.addLayout(top)

        self._table = QTableWidget(0, 6, self)
        self._table.setHorizontalHeaderLabels(
            ["插件 ID", "名称", "分类", "版本", "状态", "依赖 / 说明"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table, 3)

        buttons = QHBoxLayout()
        self._install_button = QPushButton("安装文件夹…", self)
        self._enable_button = QPushButton("启用", self)
        self._disable_button = QPushButton("禁用", self)
        self._uninstall_button = QPushButton("卸载", self)
        close_button = QPushButton("关闭", self)
        self._install_button.clicked.connect(self._install)
        self._enable_button.clicked.connect(self._enable)
        self._disable_button.clicked.connect(self._disable)
        self._uninstall_button.clicked.connect(self._uninstall)
        close_button.clicked.connect(self.accept)
        for button in (
            self._install_button,
            self._enable_button,
            self._disable_button,
            self._uninstall_button,
            close_button,
        ):
            buttons.addWidget(button)
        layout.addLayout(buttons)

        layout.addWidget(QLabel("内核日志（含依赖缺失、加载失败、回滚记录）：", self))
        self._log = QPlainTextEdit(self)
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(300)
        layout.addWidget(self._log, 1)

        self._refresh()

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        categories = self.kernel.categories()
        current = self._filter.currentData() or ALL_CATEGORIES
        self._filter.blockSignals(True)
        self._filter.clear()
        self._filter.addItem("全部分类", ALL_CATEGORIES)
        for category in categories:
            self._filter.addItem(f"{category.label} ({category.id})", category.id)
        index = self._filter.findData(current)
        self._filter.setCurrentIndex(index if index >= 0 else 0)
        self._filter.blockSignals(False)

        selected = self._filter.currentData() or ALL_CATEGORIES
        self._table.setRowCount(0)
        for pid, record in sorted(self.kernel.records.items()):
            manifest = record.manifest
            if selected != ALL_CATEGORIES and manifest.category.id != selected:
                continue
            row = self._table.rowCount()
            self._table.insertRow(row)
            dependencies = ", ".join(
                f"{key} ({value})" for key, value in manifest.dependencies.items()
            ) or "—"
            detail = record.message or manifest.description or dependencies
            values = [
                pid,
                manifest.name,
                f"{manifest.category.label} [{manifest.category.id}]",
                manifest.version,
                {"enabled": "已启用", "disabled": "已禁用", "failed": "加载失败"}.get(
                    record.state, record.state
                ),
                f"{dependencies} · {detail}",
            ]
            for column, text in enumerate(values):
                item = QTableWidgetItem(text)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, pid)
                self._table.setItem(row, column, item)
        self._table.resizeColumnsToContents()
        self._log.setPlainText("\n".join(self.kernel.logs[-120:]))

    def _selected_id(self) -> str | None:
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先在列表中选择一个插件")
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _guard(self, action) -> None:
        try:
            result = action()
            if isinstance(result, OperationResult) and not result.ok:
                QMessageBox.warning(self, "插件操作未成功", result.message)
        except KernelError as exc:
            QMessageBox.warning(self, "插件操作被拒绝", str(exc))
        except Exception as exc:  # noqa: BLE001 - 管理界面的任何异常都不拖垮壳子
            QMessageBox.critical(self, "插件操作异常（已隔离）", repr(exc))
        finally:
            self._refresh()

    # ------------------------------------------------------------------
    def _install(self) -> None:
        samples = Path(__file__).resolve().parents[1] / "sample_plugins"
        directory = QFileDialog.getExistingDirectory(
            self, "选择插件文件夹（必须含 manifest.json）", str(samples)
        )
        if not directory:
            return
        self._guard(lambda: self.kernel.install(Path(directory)))

    def _enable(self) -> None:
        pid = self._selected_id()
        if pid:
            self._guard(lambda: self.kernel.enable(pid))

    def _disable(self) -> None:
        pid = self._selected_id()
        if pid:
            self._guard(lambda: self.kernel.disable(pid))

    def _uninstall(self) -> None:
        pid = self._selected_id()
        if not pid:
            return
        answer = QMessageBox.question(
            self,
            "确认卸载",
            f"确定卸载插件 {pid} 吗？其目录与全部运行时副作用都会被清理。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._guard(lambda: self.kernel.uninstall(pid))
