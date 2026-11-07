"""PluginShell 微内核包：纯 Python，不 import 任何 GUI / Web 技术。

只负责：插件发现、加载/卸载、依赖解析、生命周期、事件总线、服务容器、扩展点注册。
不含任何业务功能，也不内置任何业务插件。
"""
from .kernel import Kernel, OperationResult, PluginRecord

__all__ = ["Kernel", "OperationResult", "PluginRecord"]
