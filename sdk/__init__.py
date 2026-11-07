"""插件 SDK 公共导出。插件作者只需：from sdk import Plugin, content_panel"""
from .api import (
    EventsView,
    ExtensionsView,
    Plugin,
    PluginContext,
    ServicesView,
    content_panel,
)

__all__ = [
    "Plugin",
    "PluginContext",
    "EventsView",
    "ServicesView",
    "ExtensionsView",
    "content_panel",
]
