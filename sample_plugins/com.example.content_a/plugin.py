"""示例插件 A —— 分类：知识点讲解（lesson）。

演示：main.content 内容贡献 + 服务容器注册 + 事件订阅/发布。
Qt 只在内容工厂内部延迟导入，因此插件模块在无界面环境也能被内核加载与验收。
"""
from __future__ import annotations

from sdk import Plugin, content_panel


class _KnowledgeService:
    """A 对外提供的服务：B 通过服务容器注入它，而不是直接 import A。"""

    def __init__(self, topic: str):
        self.topic = topic
        self.clicks = 0
        self.last_refresh = None

    def get_topic(self) -> str:
        return self.topic

    def snapshot(self) -> dict:
        return {"topic": self.topic, "clicks": self.clicks}


class ContentAPlugin(Plugin):
    def activate(self, context) -> None:
        self.context = context
        self._label = None
        self.service = _KnowledgeService("二次函数 y = ax² + bx + c")
        context.services.register("com.example.content_a.api", self.service)
        context.events.subscribe("knowledge.refresh_request", self._on_refresh_request)
        context.extensions.contribute(
            "main.content",
            content_panel(
                "com.example.content_a.panel",
                "知识点讲解 · 二次函数",
                self._build_panel,
                category="lesson",
                order=10,
            ),
        )
        context.log("知识点讲解插件已激活")

    def _on_refresh_request(self, event: str, payload) -> None:
        self.service.last_refresh = payload
        self.context.log(f"收到 {event}: {payload!r}")

    def publish_update(self) -> None:
        """供 UI 按钮与自动化测试调用：向事件总线广播一次知识点更新。"""
        self.service.clicks += 1
        self.context.events.publish("knowledge.updated", self.service.snapshot())
        if self._label is not None:
            self._label.setText(f"已发布 {self.service.clicks} 次知识点更新（工具插件会同步收到）")

    def _build_panel(self, parent):
        from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(self.service.get_topic(), widget))
        layout.addWidget(
            QLabel("顶点式、判别式 Δ=b²-4ac 与图像开口方向是该知识点的常见考点。", widget)
        )
        self._label = QLabel("尚未发布更新", widget)
        button = QPushButton("发布知识点更新（事件总线）", widget)
        button.clicked.connect(self.publish_update)
        layout.addWidget(self._label)
        layout.addWidget(button)
        layout.addStretch(1)
        return widget

    def deactivate(self) -> None:
        self._label = None
