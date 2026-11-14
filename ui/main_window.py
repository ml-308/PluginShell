"""壳子主窗口（PySide6 原生 QWidget，无任何 Web 技术）。

职责仅限两件事：
1) 空状态：未安装/未启用插件时显示"请安装插件"与插件管理入口；
2) 渲染 main.content 扩展点贡献，并按插件自报的分类做通用筛选导航。

窗口本身不贡献任何扩展点、不注册任何服务，也不认识任何具体业务分类。
"""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import update_check

from .plugin_manager import PluginManagerDialog

ALL_CATEGORIES = "__all__"


class MainWindow(QMainWindow):
    def __init__(self, kernel):
        super().__init__()
        self.kernel = kernel
        self._active_category = ALL_CATEGORIES
        self._pending = False

        self.setWindowTitle("PluginShell · 原生插件壳子")
        self.resize(980, 660)

        central = QWidget(self)
        root_layout = QHBoxLayout(central)

        self._nav = QListWidget(central)
        self._nav.setMaximumWidth(210)
        self._nav.currentItemChanged.connect(self._on_category_changed)
        root_layout.addWidget(self._nav)

        self._host = QWidget(central)
        self._host_layout = QVBoxLayout(self._host)
        self._host_layout.setContentsMargins(12, 12, 12, 12)
        self._host_layout.setSpacing(12)
        scroll = QScrollArea(central)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._host)
        root_layout.addWidget(scroll, 1)
        self.setCentralWidget(central)

        toolbar = self.addToolBar("壳子")
        manage_action = QAction("插件管理…", self)
        manage_action.triggered.connect(self._open_manager)
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self._render)
        toolbar.addAction(manage_action)
        toolbar.addAction(refresh_action)
        update_action = QAction("检查更新…", self)
        update_action.triggered.connect(lambda: update_check.check_now(self))
        toolbar.addAction(update_action)
        self.statusBar().showMessage("就绪")

        self._kernel_token = kernel.on_changed(self._schedule_render)
        self._extension_token = kernel.extensions.on_changed(self._schedule_render)
        self._render()

    # ------------------------------------------------------------------
    # 分类导航（数据源只有插件清单）
    # ------------------------------------------------------------------
    def _category_of(self, contribution) -> str:
        payload = contribution.payload
        declared = payload.get("category")
        if declared:
            return str(declared)
        record = self.kernel.records.get(contribution.owner)
        return record.manifest.category.id if record else "general"

    def _rebuild_navigation(self) -> None:
        contributions = self.kernel.extensions.contributions("main.content")
        categories = self.kernel.categories(enabled_only=True)
        self._nav.blockSignals(True)
        self._nav.clear()

        all_item = QListWidgetItem(f"全部  ({len(contributions)})")
        all_item.setData(Qt.ItemDataRole.UserRole, ALL_CATEGORIES)
        self._nav.addItem(all_item)
        for category in categories:
            count = sum(1 for c in contributions if self._category_of(c) == category.id)
            item = QListWidgetItem(f"{category.label}  ({count})")
            item.setData(Qt.ItemDataRole.UserRole, category.id)
            self._nav.addItem(item)

        target_row = 0
        if self._active_category != ALL_CATEGORIES:
            for row in range(self._nav.count()):
                if self._nav.item(row).data(Qt.ItemDataRole.UserRole) == self._active_category:
                    target_row = row
                    break
            else:
                self._active_category = ALL_CATEGORIES
        self._nav.setCurrentRow(target_row)
        self._nav.blockSignals(False)

    def _on_category_changed(self, current, _previous) -> None:
        if current is None:
            return
        self._active_category = current.data(Qt.ItemDataRole.UserRole) or ALL_CATEGORIES
        self._render_content()

    # ------------------------------------------------------------------
    # 内容渲染
    # ------------------------------------------------------------------
    def _schedule_render(self) -> None:
        if self._pending:
            return
        self._pending = True
        QTimer.singleShot(0, self._deferred_render)

    def _deferred_render(self) -> None:
        self._pending = False
        self._render()

    def _render(self) -> None:
        self._rebuild_navigation()
        self._render_content()

    def _clear_host(self) -> None:
        while self._host_layout.count():
            item = self._host_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _empty_state(self) -> QWidget:
        widget = QWidget(self._host)
        layout = QVBoxLayout(widget)
        title = QLabel("请安装插件", widget)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = title.font()
        font.setPointSize(22)
        font.setBold(True)
        title.setFont(font)
        hint = QLabel("当前壳子没有任何业务内容；所有内容都必须由插件提供。", widget)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button = QPushButton("打开插件管理…", widget)
        button.setMaximumWidth(220)
        button.clicked.connect(self._open_manager)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addSpacing(10)
        layout.addWidget(hint)
        layout.addSpacing(18)
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        return widget

    def _render_content(self) -> None:
        self._clear_host()
        all_contributions = self.kernel.extensions.contributions("main.content")

        if not all_contributions:
            self._host_layout.addWidget(self._empty_state())
            self.statusBar().showMessage("空壳状态：未安装/未启用任何内容插件")
            return

        visible = [
            c
            for c in all_contributions
            if self._active_category == ALL_CATEGORIES
            or self._category_of(c) == self._active_category
        ]
        if not visible:
            label = QLabel("该分类暂无内容", self._host)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._host_layout.addWidget(label)
        else:
            for contribution in sorted(
                visible, key=lambda c: (c.payload.get("order", 100), c.payload.get("id", ""))
            ):
                payload = contribution.payload
                box = QGroupBox(str(payload.get("title") or contribution.owner), self._host)
                box_layout = QVBoxLayout(box)
                try:
                    factory = payload.get("factory")
                    if not callable(factory):
                        raise RuntimeError("贡献内容缺少可调用的 factory")
                    widget = factory(box)
                    if widget is None:
                        raise RuntimeError("内容工厂未返回 QWidget")
                    box_layout.addWidget(widget)
                except Exception as exc:  # noqa: BLE001 - 单个插件渲染失败不影响壳子
                    box_layout.addWidget(
                        QLabel(f"[插件内容渲染失败，已隔离] {exc!r}", box)
                    )
                self._host_layout.addWidget(box)

        self._host_layout.addStretch(1)
        category_count = len(self.kernel.categories(enabled_only=True))
        self.statusBar().showMessage(
            f"已安装 {len(self.kernel.records)} · 已启用 {len(self.kernel.enabled)} · "
            f"分类 {category_count} · 当前显示 {len(visible)}/{len(all_contributions)} 个内容贡献"
        )

    # ------------------------------------------------------------------
    def _open_manager(self) -> None:
        dialog = PluginManagerDialog(self.kernel, self)
        dialog.exec()
        self._schedule_render()

    def closeEvent(self, event) -> None:
        self.kernel.off_changed(self._kernel_token)
        self.kernel.extensions.off_changed(self._extension_token)
        event.accept()
