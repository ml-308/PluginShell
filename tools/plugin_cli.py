"""无 GUI 的插件管理命令（微内核的另一套管理入口）。

    python tools/plugin_cli.py list [--category lab]
    python tools/plugin_cli.py install <插件文件夹>
    python tools/plugin_cli.py enable <插件ID>
    python tools/plugin_cli.py disable <插件ID>
    python tools/plugin_cli.py uninstall <插件ID>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001 - 部分终端不支持重配置
    pass

from core.errors import KernelError  # noqa: E402
from core.kernel import Kernel  # noqa: E402


def make_kernel() -> Kernel:
    return Kernel(
        plugins_dir=ROOT / "plugins",
        project_root=ROOT,
        state_path=ROOT / "state" / "enabled.json",
        log_sink=print,
    )


def print_list(kernel: Kernel, category: str | None) -> None:
    ids = (
        set(kernel.plugins_by_category(category))
        if category
        else set(kernel.records)
    )
    print(f"插件目录: {kernel.plugins_dir}")
    print(f"已安装 {len(kernel.records)} 个 / 已启用 {len(kernel.enabled)} 个"
          + (f" / 分类筛选: {category}" if category else ""))
    print("-" * 100)
    for pid in sorted(ids):
        record = kernel.records[pid]
        manifest = record.manifest
        print(
            f"{pid:<38} v{manifest.version:<8} "
            f"[{manifest.category.label}/{manifest.category.id}] "
            f"{record.state:<9} 依赖={list(manifest.dependencies) or '—'}"
        )
        if record.message:
            print(f"    ! {record.message}")
    print("-" * 100)
    print("分类:", ", ".join(f"{c.label}({c.id})" for c in kernel.categories()) or "（无）")
    print("扩展点:", ", ".join(kernel.extensions.points()))
    print("内容贡献:", len(kernel.extensions.contributions("main.content")))
    print("已注册服务:", ", ".join(kernel.services.names()) or "（无）")
    print("事件订阅数:", kernel.bus.handler_count())


def main() -> int:
    parser = argparse.ArgumentParser(description="PluginShell 插件管理命令")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="列出插件与内核状态")
    list_parser.add_argument("--category", help="按分类 ID 筛选，如 lesson / tool / lab")

    install_parser = sub.add_parser("install", help="安装文件夹形式的插件")
    install_parser.add_argument("path")

    for name in ("enable", "disable", "uninstall"):
        command = sub.add_parser(name, help=f"{name} 插件")
        command.add_argument("plugin_id")

    args = parser.parse_args()
    kernel = make_kernel()
    try:
        kernel.bootstrap()
        if args.command == "list":
            print_list(kernel, args.category)
            return 0
        try:
            if args.command == "install":
                result = kernel.install(Path(args.path))
                print(("OK: " if result.ok else "WARN: ") + result.message)
                return 0 if result.ok else 1
            if args.command == "enable":
                kernel.enable(args.plugin_id)
            elif args.command == "disable":
                kernel.disable(args.plugin_id)
            elif args.command == "uninstall":
                kernel.uninstall(args.plugin_id)
            print(f"OK: {args.command} {args.plugin_id}")
            return 0
        except KernelError as exc:
            print(f"ERROR: {exc}")
            return 1
    finally:
        kernel.shutdown()


if __name__ == "__main__":
    sys.exit(main())
