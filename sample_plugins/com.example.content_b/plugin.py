"""示例插件 B —— 分类：工具（tool），依赖插件 A。

演示：依赖声明 + 服务容器注入 + 事件总线协作。
B 从不 import A，A 也从不 import B：两者只通过内核的两个通道通信。
"""
from __future__ import annotations

from sdk import Plugin, content_panel


class ContentBPlugin(Plugin):
    def activate(self, context) -> None:
        self.context = context
        self._label = None
        self.received = 0
        # 服务容器：拿到 A 注册的服务对象（不直接引用 A 的模块）
        self.api = context.services.require("com.example.content_a.api")
        # 事件总线：订阅 A 发布的事件
        context.events.subscribe("knowledge.updated", self._on_knowledge_updated)
        context.extensions.contribute(
            "main.content",
            content_panel(
                "com.example.content_b.panel",
                "工具 · 知识点速记",
                self._build_panel,
                category="tool",
                order=20,
            ),
        )
        context.log(f"工具插件已激活，注入服务成功，当前知识点：{self.api.get_topic()}")

    def _on_knowledge_updated(self, event: str, payload) -> None:
        self.received += 1
        self.context.events.publish(
            "tool.sync_ack", {"received": self.received, "source": payload}
        )
        if self._label is not None:
            self._label.setText(
                f"已同步 {self.received} 次 · 来自服务的知识点：{self.api.get_topic()}"
            )

    def request_refresh(self) -> None:
        """反向协作：B 发布请求事件，A 订阅该事件。"""
        self.context.events.publish("knowledge.refresh_request", {"requester": "B"})

    def _build_panel(self, parent):
        from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("随堂速记：本工具的数据全部来自插件 A 提供的服务。", widget))
        self._label = QLabel(f"已同步 0 次 · 当前知识点：{self.api.get_topic()}", widget)
        button = QPushButton("读取 A 的服务并向 A 请求刷新", widget)
        button.clicked.connect(self._on_button)
        layout.addWidget(self._label)
        layout.addWidget(button)
        layout.addStretch(1)
        return widget

    def _on_button(self) -> None:
        self.request_refresh()
        if self._label is not None:
            self._label.setText(f"服务返回：{self.api.get_topic()}（已发送刷新请求）")

    def deactivate(self) -> None:
        self._label = None
