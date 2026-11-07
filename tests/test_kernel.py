"""最小自动化验收套件（纯 Python，无需 PySide6 / 显示器 / 网络）。

覆盖：空壳启动、安装 A 后出现内容、卸载 A 后完全回滚、B 依赖 A、
禁用后副作用回滚、加载失败隔离、清单声明强制、分类来自插件、无 Web 技术、启动恢复。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.errors import DependencyError  # noqa: E402
from core.kernel import Kernel  # noqa: E402
from core.manifest import parse_manifest  # noqa: E402
from core.resolver import resolve_load_order  # noqa: E402

SAMPLES = ROOT / "sample_plugins"
A = "com.example.content_a"
B = "com.example.content_b"
C = "com.example.lab_coordinate"


class BaseKernelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.plugins_dir = Path(self.tmp.name) / "plugins"
        self.kernel = Kernel(
            plugins_dir=self.plugins_dir, project_root=ROOT, state_path=None
        )
        self.kernel.bootstrap()

    def tearDown(self) -> None:
        self.kernel.shutdown()
        self.tmp.cleanup()

    def install(self, plugin_id: str):
        return self.kernel.install(SAMPLES / plugin_id)

    def _make_faulty_plugin(self, plugin_id: str, extra: dict, code: str) -> Path:
        directory = Path(self.tmp.name) / "src" / plugin_id
        directory.mkdir(parents=True, exist_ok=True)
        manifest = {
            "id": plugin_id,
            "name": plugin_id,
            "version": "1.0.0",
            "api": "1.0",
            "entry": "plugin.py",
            "class": "BadPlugin",
        }
        manifest.update(extra)
        (directory / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (directory / "plugin.py").write_text(code, encoding="utf-8")
        return directory


class ShellAcceptanceTests(BaseKernelTest):
    def test_01_empty_shell_starts_without_business_content(self) -> None:
        self.assertEqual(self.kernel.records, {})
        self.assertEqual(self.kernel.enabled, set())
        self.assertEqual(self.kernel.extensions.contributions("main.content"), ())
        self.assertEqual(self.kernel.services.names(), ())
        self.assertEqual(self.kernel.bus.handler_count(), 0)
        self.assertEqual(self.kernel.categories(), ())
        # 内核只预置通用扩展点，不预置任何业务内容
        self.assertEqual(self.kernel.extensions.points(), ("main.content",))

    def test_02_install_a_shows_content(self) -> None:
        result = self.install(A)
        self.assertTrue(result.ok, result.message)
        contributions = self.kernel.extensions.contributions("main.content")
        self.assertEqual(len(contributions), 1)
        self.assertEqual(contributions[0].payload["id"], "com.example.content_a.panel")
        self.assertEqual(contributions[0].owner, A)
        self.assertIn("com.example.content_a.api", self.kernel.services.names())
        self.assertEqual(self.kernel.bus.handler_count("knowledge.refresh_request"), 1)
        self.assertEqual({c.id for c in self.kernel.categories()}, {"lesson"})

        # 事件总线：宿主发布 A 声明订阅的事件，A 应收到
        self.kernel.bus.publish("knowledge.refresh_request", {"from": "test"})
        instance = self.kernel.records[A].instance
        self.assertEqual(instance.service.last_refresh, {"from": "test"})

    def test_03_uninstall_a_restores_empty_shell(self) -> None:
        self.install(A)
        self.kernel.uninstall(A)
        self.assertEqual(self.kernel.records, {})
        self.assertEqual(self.kernel.extensions.contributions("main.content"), ())
        self.assertEqual(self.kernel.services.names(), ())
        self.assertEqual(self.kernel.bus.handler_count(), 0)
        self.assertEqual(self.kernel.categories(), ())
        self.assertEqual(list(self.plugins_dir.iterdir()), [])
        self.assertFalse(any(k.startswith("_pluginshell_") for k in sys.modules))

    def test_04_b_without_a_is_refused_with_clear_message(self) -> None:
        result = self.install(B)
        self.assertFalse(result.ok)
        self.assertIn("缺少依赖插件", result.message)
        self.assertIn(A, result.message)
        self.assertEqual(self.kernel.records[B].state, "failed")
        self.assertIn("缺少依赖插件", self.kernel.records[B].message)
        self.assertEqual(self.kernel.extensions.contributions("main.content"), ())
        # 壳子仍可继续安装其它插件，故障被隔离
        self.assertTrue(self.install(A).ok)

    def test_05_a_and_b_collaborate_via_bus_and_services(self) -> None:
        self.assertTrue(self.install(A).ok)
        self.assertTrue(self.install(B).ok)
        self.assertEqual(self.kernel.enabled, {A, B})
        self.assertEqual(len(self.kernel.extensions.contributions("main.content")), 2)
        self.assertEqual({c.id for c in self.kernel.categories()}, {"lesson", "tool"})
        self.assertEqual(self.kernel.plugins_by_category("tool"), (B,))

        ack = []
        self.kernel.bus.subscribe("tool.sync_ack", lambda _e, payload: ack.append(payload))
        instance_a = self.kernel.records[A].instance
        instance_b = self.kernel.records[B].instance
        self.assertEqual(instance_b.api, instance_a.service)  # 服务容器注入

        instance_a.publish_update()  # A 发布事件 -> B 订阅并回 ack
        self.assertEqual(instance_b.received, 1)
        self.assertEqual(len(ack), 1)
        self.assertEqual(ack[0]["source"]["clicks"], 1)

        instance_b.request_refresh()  # B 发布请求 -> A 订阅
        self.assertEqual(instance_a.service.last_refresh, {"requester": "B"})

    def test_06_disable_rolls_back_every_side_effect(self) -> None:
        for pid in (A, B, C):
            self.assertTrue(self.install(pid).ok)
        self.assertEqual(len(self.kernel.extensions.contributions("main.content")), 3)
        self.assertIn("lab.canvas.tools", self.kernel.extensions.points())

        # 被依赖方不能直接停用：阻止并明确提示
        with self.assertRaises(DependencyError) as ctx:
            self.kernel.disable(A)
        self.assertIn(B, str(ctx.exception))

        self.kernel.disable(B)
        self.assertEqual(self.kernel.bus.handler_count("knowledge.updated"), 0)
        self.assertEqual(
            {c.owner for c in self.kernel.extensions.contributions("main.content")},
            {A, C},
        )

        self.kernel.disable(A)
        self.assertNotIn("com.example.content_a.api", self.kernel.services.names())
        self.assertEqual(self.kernel.bus.handler_count("knowledge.refresh_request"), 0)

        self.kernel.disable(C)
        self.assertEqual(self.kernel.extensions.contributions("main.content"), ())
        self.assertEqual(self.kernel.extensions.points(), ("main.content",))
        self.assertEqual(self.kernel.services.names(), ())
        self.assertEqual(self.kernel.bus.handler_count(), 0)
        self.assertEqual(self.kernel.categories(enabled_only=True), ())
        self.assertFalse(any(k.startswith("_pluginshell_") for k in sys.modules))

    def test_07_uninstall_blocked_by_installed_dependent(self) -> None:
        self.install(A)
        self.install(B)
        with self.assertRaises(DependencyError) as ctx:
            self.kernel.uninstall(A)
        self.assertIn(B, str(ctx.exception))
        self.assertTrue((self.plugins_dir / A).is_dir())
        self.kernel.uninstall(B)
        self.kernel.uninstall(A)
        self.assertEqual(self.kernel.records, {})
        self.assertEqual(self.kernel.extensions.contributions("main.content"), ())

    def test_08_load_failure_is_isolated(self) -> None:
        faulty = self._make_faulty_plugin(
            "com.test.boom",
            {},
            "from sdk import Plugin\n"
            "class BadPlugin(Plugin):\n"
            "    def activate(self, context):\n"
            "        raise RuntimeError('boom')\n",
        )
        result = self.kernel.install(faulty)
        self.assertFalse(result.ok)
        self.assertIn("加载失败", result.message)
        self.assertEqual(self.kernel.records["com.test.boom"].state, "failed")
        self.assertEqual(self.kernel.bus.handler_count(), 0)
        self.assertTrue(self.install(A).ok)  # 内核没被拖垮
        self.assertEqual(len(self.kernel.extensions.contributions("main.content")), 1)

    def test_09_manifest_declaration_is_enforced(self) -> None:
        faulty = self._make_faulty_plugin(
            "com.test.undeclared",
            {},
            "from sdk import Plugin\n"
            "class BadPlugin(Plugin):\n"
            "    def activate(self, context):\n"
            "        context.events.subscribe('secret.event', lambda e, p: None)\n",
        )
        result = self.kernel.install(faulty)
        self.assertFalse(result.ok)
        self.assertIn("未在 manifest.subscribes 声明", result.message)
        self.assertEqual(self.kernel.bus.handler_count("secret.event"), 0)

    def test_10_categories_are_generic_and_no_web_or_business_in_core(self) -> None:
        for pid in (A, B, C):
            self.assertTrue(self.install(pid).ok)
        self.assertEqual(
            {c.id for c in self.kernel.categories()}, {"lesson", "tool", "lab"}
        )
        self.assertEqual(self.kernel.plugins_by_category("lab"), (C,))
        self.kernel.uninstall(C)
        self.assertNotIn("lab", {c.id for c in self.kernel.categories()})

        business_words = ["知识点讲解", "实验室", "平面直角坐标系", "二次函数", "理化"]
        core_and_ui = [p for folder in ("core", "ui") for p in (ROOT / folder).rglob("*.py")]
        core_and_ui.append(ROOT / "run.py")
        for path in core_and_ui:
            text = path.read_text(encoding="utf-8")
            for word in business_words:
                self.assertNotIn(word, text, f"{path.name} 中出现了业务硬编码: {word}")

        forbidden = ["QWebEngineView", "QWebView", "WebView", "Electron", "<html", "<script"]
        for path in ROOT.rglob("*"):
            if path.suffix in (".html", ".htm", ".css", ".js"):
                self.fail(f"出现 Web 前端文件: {path}")
            if path.suffix == ".py" and "tests" not in path.parts:
                text = path.read_text(encoding="utf-8")
                for token in forbidden:
                    self.assertNotIn(token, text, f"{path.name} 出现 Web 技术: {token}")

    def test_11_bootstrap_restores_enabled_set_by_topological_order(self) -> None:
        state_path = Path(self.tmp.name) / "state" / "enabled.json"
        first = Kernel(
            plugins_dir=self.plugins_dir, project_root=ROOT, state_path=state_path
        )
        first.bootstrap()
        first.install(SAMPLES / A)
        first.shutdown()
        self.assertTrue(state_path.is_file())

        second = Kernel(
            plugins_dir=self.plugins_dir, project_root=ROOT, state_path=state_path
        )
        second.bootstrap()
        self.addCleanup(second.shutdown)
        self.assertEqual(second.enabled, {A})
        self.assertEqual(len(second.extensions.contributions("main.content")), 1)
        self.assertIn("com.example.content_a.api", second.services.names())

    def test_12_resolver_detects_cycles_and_missing_dependencies(self) -> None:
        def manifest(pid: str, deps: dict):
            return parse_manifest(
                {
                    "id": pid,
                    "name": pid,
                    "version": "1.0.0",
                    "api": "1.0",
                    "entry": "plugin.py",
                    "class": "X",
                    "dependencies": deps,
                }
            )

        with self.assertRaises(DependencyError) as ctx:
            resolve_load_order({"a"}, {"a": manifest("a", {"b": ">=1.0.0"})})
        self.assertIn("缺少依赖插件 b", str(ctx.exception))

        with self.assertRaises(DependencyError) as ctx:
            resolve_load_order(
                {"a"}, {"a": manifest("a", {"b": "*"}), "b": manifest("b", {"a": "*"})}
            )
        self.assertIn("循环依赖", str(ctx.exception))

        order = resolve_load_order(
            {"c"},
            {
                "a": manifest("a", {}),
                "b": manifest("b", {"a": ">=1.0.0"}),
                "c": manifest("c", {"b": "*"}),
            },
        )
        self.assertEqual(order, ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
