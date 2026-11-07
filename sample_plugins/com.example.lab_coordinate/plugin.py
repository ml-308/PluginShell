"""示例插件 C —— 分类：实验室（lab）。

用 Qt QPainter 原生绘制平面直角坐标系与可交互抛物线；同时注册一个自定义
扩展点，用来验证"扩展点注册"也属于可回滚的副作用。
整个实现位于插件内，内核不知道坐标系、实验室或任何学科概念。
"""
from __future__ import annotations

from sdk import Plugin, content_panel


class LabCoordinatePlugin(Plugin):
    def activate(self, context) -> None:
        self.context = context
        self.param = 1.0
        self._canvas = None
        self._info = None
        context.extensions.define_point("lab.canvas.tools", "实验画布工具扩展点")
        context.extensions.contribute(
            "main.content",
            content_panel(
                "com.example.lab_coordinate.panel",
                "实验室 · 平面直角坐标系",
                self._build_panel,
                category="lab",
                order=30,
            ),
        )
        context.log("平面直角坐标系实验室已激活")

    def _on_slider(self, value: int) -> None:
        self.param = value / 10.0
        if self._info is not None:
            self._info.setText(f"y = {self.param:.1f} · x²，拖动滑块实时重绘")
        if self._canvas is not None:
            self._canvas.update()

    def _build_panel(self, parent):
        # 延迟导入：插件模块本身保持纯 Python，便于无界面验收
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QColor, QPainter, QPen
        from PySide6.QtWidgets import QLabel, QSlider, QVBoxLayout, QWidget

        plugin = self

        class _CoordinateCanvas(QWidget):
            def __init__(self, parent_widget):
                super().__init__(parent_widget)
                self.setMinimumHeight(260)

            def paintEvent(self, _event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                width, height = self.width(), self.height()
                cx, cy = width / 2.0, height / 2.0
                unit = max(12.0, min(width, height) / 14.0)
                foreground = self.palette().text().color()

                grid_pen = QPen(foreground)
                grid_pen.setStyle(Qt.PenStyle.DotLine)
                grid_pen.setWidthF(0.7)
                painter.setPen(grid_pen)
                for index in range(-24, 25):
                    x = cx + index * unit
                    if 0 <= x <= width:
                        painter.drawLine(int(x), 0, int(x), height)
                    y = cy + index * unit
                    if 0 <= y <= height:
                        painter.drawLine(0, int(y), width, int(y))

                axis_pen = QPen(foreground)
                axis_pen.setWidth(2)
                painter.setPen(axis_pen)
                painter.drawLine(0, int(cy), width, int(cy))
                painter.drawLine(int(cx), 0, int(cx), height)
                painter.drawText(int(cx) + 6, int(cy) - 8, "0  x")
                painter.drawText(int(cx) + 6, 16, "y")

                curve_pen = QPen(QColor(218, 86, 86))
                curve_pen.setWidth(2)
                painter.setPen(curve_pen)
                previous = None
                for step in range(-300, 301):
                    x = step / 50.0
                    point = QPointF(
                        cx + x * unit,
                        cy - plugin.param * x * x * unit / 2.0,
                    )
                    if previous is not None:
                        painter.drawLine(previous, point)
                    previous = point
                painter.end()

        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        self._info = QLabel("y = 1.0 · x²，拖动滑块实时重绘", widget)
        self._canvas = _CoordinateCanvas(widget)
        slider = QSlider(Qt.Orientation.Horizontal, widget)
        slider.setRange(-30, 30)
        slider.setValue(10)
        slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self._info)
        layout.addWidget(self._canvas, 1)
        layout.addWidget(slider)
        return widget

    def deactivate(self) -> None:
        self._canvas = None
        self._info = None
