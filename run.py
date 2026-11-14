"""PluginShell 启动入口。

    python run.py

未安装插件时启动即为空壳：只显示"请安装插件"与插件管理入口。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 「发现新版本」检查：命令行开关 + 无人值守 probe（不依赖 Qt，可在无 GUI 环境跑）
import update_check  # noqa: E402

update_check.configure(sys.argv)
_probe_exit = update_check.try_probe(sys.argv)
if _probe_exit is not None:
    sys.exit(_probe_exit)

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    print("缺少原生 GUI 依赖 PySide6。请先执行： pip install -r requirements.txt")
    print("（微内核与自动化测试是纯 Python，可在未安装 PySide6 时运行）")
    sys.exit(2)

from core.kernel import Kernel  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    kernel = Kernel(
        plugins_dir=ROOT / "plugins",
        project_root=ROOT,
        state_path=ROOT / "state" / "enabled.json",
    )
    kernel.bootstrap()

    app = QApplication(sys.argv)
    window = MainWindow(kernel)
    window.show()
    update_check.schedule_auto_check(window)
    return_code = app.exec()
    kernel.shutdown()
    return return_code


if __name__ == "__main__":
    sys.exit(main())
