# PluginShell · 原生「一切皆插件」微内核壳子

一个面向**高中各科知识点展示**的桌面 App 壳子：壳子本身只有空状态与插件管理能力，
知识点讲解、学习工具、理化/坐标系实验室等**全部业务内容都由插件提供**。

> 技术栈：**Python 3.10+ / PySide6（Qt for Python，原生桌面 GUI）**。
> 你未指定技术栈，按约定采用默认；选它是因为 Qt 提供纯原生 QWidget/QPainter 绘制能力，
> 可完全避开 Web 技术，同时 `core/` 可以做成零 GUI 依赖的纯 Python 微内核，便于无界面验收。
>
> **全程无 HTML / CSS / JS / 浏览器 / WebView / Electron。** 内核与自动化测试连 Qt 都不需要。

---

## 1. 硬性约束如何落地

| 约束 | 实现 |
| --- | --- |
| 不是 Web 应用 | UI 全部为 PySide6 `QWidget`/`QPainter`；无 Web 视图、无浏览器进程、无前端资源文件 |
| 空壳允许为空 | `plugins/` 初始为空；主区域只有「请安装插件」+「打开插件管理…」 |
| 核心无业务功能 | `core/` 不含任何学科名词、任何分类 ID、任何示例插件引用；自动化测试静态检查这一点 |
| 示例业务也是插件 | A/B/C 位于 `sample_plugins/`，与第三方插件走**完全相同**的安装通道，无任何特权 |
| 微内核职责 | 仅：发现 / 加载卸载 / 依赖解析 / 生命周期 / 事件总线 / 服务容器 / 扩展点注册 |
| 核心无特权 | 只有一份 `sdk.api.Plugin` 协议；内核不向任何扩展点贡献内容，也没有"官方插件"路径 |
| 静态声明 | `manifest.json` 声明 ID、版本、依赖、分类、扩展点贡献、注入服务、订阅/发布事件；运行期由 `PluginContext` 强制校验 |
| 插件不直接引用 | A 与 B 互不 import，只通过事件总线 / 服务容器通信 |
| 内容扩展点 | `main.content` 由内核预定义；插件也可声明并定义自己的扩展点 |
| 副作用可逆 | 每次订阅/注册/贡献/定义扩展点都登记逆操作，卸载时逆序回滚，并清理 `sys.modules`/`sys.path` |
| 故障隔离 | 导入、激活、事件回调、UI 工厂、观察者逐层 `try/except`；失败插件标记 `failed` 并完整回滚 |
| 依赖缺失提示 | 拓扑解析阶段即拒绝，返回"缺少依赖插件 X (约束)"的明确中文原因 |

---

## 2. 快速开始

```bash
cd D:/dsh/tool/PluginShell
pip install -r requirements.txt      # 仅 GUI 需要（只装 Qt Essentials，不含 WebEngine）
python run.py                        # 直接启动 → 空壳状态
```

### 2.1 原生安装程序 setup.exe

`dist/setup.exe` 是用 **Inno Setup 6** 生成的标准 Windows 安装向导（非 Web、非自解压脚本）：
选择目录 → 释放项目文件 → 创建快捷方式 → 注册标准卸载项。默认装到
`%LOCALAPPDATA%\PluginShell`，`PrivilegesRequired=lowest` 不需要管理员权限。
安装包**不预装任何插件**，安装后首次启动仍是「请安装插件」的空壳状态。

```bash
winget install --id JRSoftware.InnoSetup --silent   # 仅首次构建需要
python installer/build.py                          # 产出 dist/setup.exe + 便携版 zip
```

`installer/Launch.cmd` 是安装后的启动器：检查 Python 与 PySide6，首次运行时自动
`pip install -r requirements.txt`（一次联网），随后 `python run.py`。
不捆绑 Python 运行时；内核、CLI、测试无需 GUI 依赖。详见 `installer/README.md`。

命令行（不需要 PySide6、不需要显示器）：

```bash
python tools/plugin_cli.py list
python tools/plugin_cli.py install sample_plugins/com.example.content_a
python tools/plugin_cli.py install sample_plugins/com.example.content_b
python tools/plugin_cli.py install sample_plugins/com.example.lab_coordinate
python tools/plugin_cli.py list --category lab
python tools/verify.py               # 12 项自动化验收
```

---

## 3. 目录结构

```
PluginShell/
├── README.md                   本文件
├── requirements.txt           PySide6（仅 UI 层）
├── run.py                      启动入口
├── core/                       微内核：纯 Python，零 Qt、零业务
│   ├── errors.py               异常体系
│   ├── manifest.py             清单解析/校验 + 版本约束求值
│   ├── resolver.py             依赖拓扑 / 循环 / 反向依赖
│   ├── bus.py                  事件总线
│   ├── services.py             服务容器
│   ├── registry.py             扩展点注册与内容贡献
│   ├── context.py               PluginContext：声明校验 + 撤销账本
│   ├── loader.py               importlib 隔离装载 + 模块卸载
│   └── kernel.py                门面：discover/install/enable/disable/uninstall/bootstrap
├── sdk/                        插件作者唯一需要依赖的公共协议
│   ├── __init__.py              from sdk import Plugin, content_panel
│   └── api.py                   Plugin / Views / PluginContext / content_panel
├── ui/                         壳子原生 Qt 界面（微内核基础设施，非业务插件）
│   ├── main_window.py           空状态 + 分类导航 + main.content 渲染
│   └── plugin_manager.py        列出/安装/启用/禁用/卸载 + 日志
├── plugins/                    运行时插件安装目录（初始为空）
├── state/                       enabled.json（启用集，运行时生成）
├── sample_plugins/             待安装示例，与第三方插件同协议
│   ├── com.example.content_a/    A：知识点讲解（lesson）
│   ├── com.example.content_b/    B：工具（tool），依赖 A
│   └── com.example.lab_coordinate/ C：实验室（lab），原生 QPainter 坐标系
├── tests/
│   ├── test_kernel.py           12 项自动化验收（无需 Qt / 显示器）
│   └── acceptance.md           手动验收清单
└── tools/
    ├── plugin_cli.py           无 GUI 插件管理命令
    └── verify.py               一键运行自动化验收
```

---

## 4. 架构图

```
┌──────────────────────── 原生壳子 UI（PySide6 QWidget，无 Web）────────────────────────┐
│ ┌── 分类导航 ──┐ ┌────────────── main.content 主内容区 ───────────────────────────┐ │
│ │ 全部        │ │ QGroupBox → 插件 factory(parent) 返回的原生 QWidget            │ │
│ │ 分类 A…     │ │ （无贡献时：请安装插件 + 插件管理入口）                        │ │
│ └─────────────┘ └────────────────────────────────────────────────────────────────┘ │
│ [插件管理…]  ← 属于微内核基础设施，不占用任何扩展点                                │
└──────────────────────┬─────────────────────────────────────────────────────────────┘
                       │ 管理命令 / 只读观察者
┌──────────────────────▼────────── 微内核 core/（纯 Python, 零 Qt）───────────────────┐
│ Kernel  discover · install · enable · disable · uninstall · bootstrap · shutdown  │
│  ├─ resolver          依赖拓扑(Kahn) / 版本约束 / 循环检测 / 反向依赖            │
│  ├─ loader            importlib 隔离装载，ModuleHandle 负责卸载                    │
│  ├─ EventBus          事件总线         ┐                                           │
│  ├─ ServiceContainer  服务容器        ├─ 插件只能通过 PluginContext 访问           │
│  ├─ ExtensionRegistry  扩展点注册表    ┘  并登记"撤销账本"（逆序回滚）              │
│  └─ PluginContext     声明校验（未声明即拒绝）+ 插件唯一的能力边界                │
└──────────────────────┬─────────────────────────────────────────────────────────────┘
                       │ 同一套插件协议，不存在官方特权通道
      ┌────────────────┼────────────────┬──────────────────────┐
      ▼                ▼                ▼                      ▼
  插件 A(lesson)   插件 B(tool)    插件 C(lab)          任意第三方插件
      └── 依赖 A ──────┘            └── 插件之间互不 import，只经事件总线 / 服务容器 ──┘
```

### 安装 → 加载流程

```
install(文件夹)
  → 校验 manifest.json（不合法则拒绝安装）
  → copytree 到 plugins/<id>/（已存在则拒绝覆盖）
  → discover() 重新扫描
  → enable(id)
      → desired = 当前启用集 ∪ {id}
      → resolve_load_order(desired)：依赖闭包 + 拓扑排序 + 版本/循环校验
      → 逆序卸载不在序列里的插件（依赖方先退）
      → 按序 _load_one()：
           检查 requires_services 是否已注册 → 检查依赖方是否已激活
           → load_plugin → Plugin() → activate(PluginContext)
           → 任一异常：context.dispose() 逆序回滚 + 模块清理 + state=failed
      → 持久化启用集 → 通知 UI 重绘
```

### 卸载 → 回滚流程

```
uninstall(id)
  → reverse_dependents(id)：存在已安装依赖方 → 阻止卸载并列出依赖方 ID
  → disable 语义：级联卸载依赖方（逆拓扑序）
  → context.dispose()：逆序执行
        撤回内容贡献 / 注销服务 / 退订事件 / 撤销自定义扩展点
  → instance.deactivate() → ModuleHandle.unload()（清理 sys.modules、sys.path）
  → 删除 plugins/<id>/ → discover() → 通知 UI
  → 结果：事件订阅数 0、服务 0、内容贡献 0、扩展点只剩内核内置点
```

---

## 5. 插件协议

### 5.1 安装形式

插件 = **一个文件夹 + `manifest.json`**，安装到 `plugins/` 下，且**目录名必须等于 `id`**。
内核只扫描一级子目录；清单损坏的目录会被跳过并记录日志，不影响其它插件。

### 5.2 `manifest.json` 字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | string | ✅ | 小写字母开头，可含数字 `. _ -`；须与目录名一致 |
| `name` | string | ✅ | 显示名 |
| `version` | string | ✅ | 形如 `1.0.0` |
| `api` | string | ✅ | 插件协议版本，当前必须为 `"1.0"` |
| `entry` | string | ✅ | 入口文件相对路径，禁止 `..` 与绝对路径 |
| `class` | string | ✅ | 入口文件中继承 `sdk.Plugin` 的类名 |
| `description` | string | | 说明 |
| **`category`** | object | | **插件自报分类**：`{id, label, order, icon}`；缺省为 `general / 未分类 / 100` |
| `dependencies` | object | | `{插件ID: 版本约束}`，支持 `>= <= == != > < = *` |
| `requires_services` | string[] | | 需要注入的服务名；激活前内核会检查它们已注册 |
| `provides_services` | string[] | | 允许本插件注册的服务名（未声明即拒绝） |
| `subscribes` | string[] | | 允许订阅的事件名 |
| `publishes` | string[] | | 允许发布的事件名 |
| `provides_extension_points` | string[] | | 允许本插件定义的扩展点名 |
| `contributes` | object | | `{扩展点名: [{id, title, category?, ...}]}`，**静态声明**贡献了哪些内容 |

> **两阶段设计**：清单静态声明"我要向哪些扩展点贡献哪些 id"；运行期 `activate()` 里再用
> `context.extensions.contribute()` 绑定真正的原生 QWidget 工厂。贡献 `id` 不在清单里会被拒绝。

### 5.3 分类机制（重点）

分类是**协议，不是内核常量**。内核只做三件通用的事：

1. 读取每个插件 `category.id / label / order`；
2. `kernel.categories(enabled_only=True)` 聚合并按 `(order, id)` 排序；
3. `kernel.plugins_by_category(category_id)` 做索引。

壳子左侧导航、插件管理表格的分类列与筛选，全部由这份聚合结果动态生成。
`core/` 与 `ui/` 源码中**不出现任何具体分类名**（自动化测试会静态校验）。

因此新增分类无需改动一行核心代码，插件只要声明：

```json
"category": { "id": "lab", "label": "实验室", "order": 30 }
```

内容贡献还可以用 `category` 字段覆盖插件默认分类，让**同一个插件向多个分类投放内容**。
`order` 同时控制导航顺序与同类内容内的展示顺序（见 `content_panel(..., order=...)`）。

示例插件据此演示了三类：`lesson` 知识点讲解、`tool` 工具、`lab` 实验室。
理化实验室、平面直角坐标系等具体形态只存在于插件里。

### 5.4 `main.content` 内容契约

`context.extensions.contribute("main.content", payload)` 的 `payload` 为 dict：

| 键 | 说明 |
| --- | --- |
| `id` | 必须与清单 `contributes.main.content[].id` 一致 |
| `title` | 面板标题（壳子用它生成 `QGroupBox` 标题） |
| `factory` | `factory(parent_widget) -> QWidget`，**壳子渲染时才调用** |
| `category` | 可选，省略时回落到插件清单的分类 |
| `order` | 可选，排序权重，默认 100 |

SDK 提供 `content_panel(...)` 生成该 dict。建议把 `from PySide6...` **放在 factory 内部**：
插件模块保持纯 Python，内核就能在无 Qt 环境下加载并验收（示例插件正是这么做的）。

### 5.5 插件基类与上下文

```python
from sdk import Plugin, content_panel

class MyPlugin(Plugin):
    def activate(self, context):
        context.events.subscribe("some.event", self._on_event)      # 必须已在 subscribes 声明
        context.events.publish("some.ack", {...})                    # 必须已在 publishes 声明
        service = context.services.require("some.service")           # 必须已在 requires_services 声明
        context.services.register("my.service", obj)                 # 必须已在 provides_services 声明
        context.extensions.define_point("my.point")                  # 必须已声明
        context.extensions.contribute("main.content", content_panel(...))
        context.log("激活完成")

    def deactivate(self):
        pass   # 只释放自有资源；上面的注册项由内核自动逆序回滚
```

`PluginContext` 暴露的只有 `plugin_id`、`manifest`、`events`、`services`、`extensions`、`log`。
插件**拿不到** `Kernel` / `EventBus` / `ServiceContainer` / `ExtensionRegistry` 本体，
因此无法绕过声明校验，也无法绕过撤销账本留下残留。

### 5.6 插件间通信

只允许两条通道，禁止 `import` 其它插件：

- **事件总线**：`events.publish(event, payload)` → 订阅者 `(event, payload)`；回调异常被隔离并写入日志。
- **服务容器**：`services.register(name, obj)` / `services.require(name)`，服务名全局唯一，注销需持有 token。

---

## 6. 依赖与生命周期规则

- **拓扑加载**：启用 B 会自动把依赖 A 纳入并按 `A → B` 顺序激活（Kahn 排序，同层按 ID 排序）。
- **缺失/版本/循环**：解析阶段即抛 `DependencyError`，UI 弹窗、CLI 打印 `ERROR:`、插件状态 `failed`。
- **停用**：存在已启用依赖方时**阻止并提示**依赖方列表；也可用 `kernel.disable(id, cascade=True)` 级联停用。
- **卸载**：存在**任何已安装**依赖方时**阻止卸载并提示**，请先卸载依赖方；卸载前按逆拓扑序回滚。
- **启动恢复**：`state/enabled.json` 记录启用集，`bootstrap()` 按拓扑序重放；记录丢失即空壳启动。
- **单向清理**：所有注册项都有 token，`dispose()` 逆序执行；模块条目也从 `sys.modules`/`sys.path` 移除。

---

## 7. 如何新增一个插件（不改任何核心代码）

1. 新建 `my_plugins/com.example.my_lesson/`（目录名 = id）。
2. 写 `manifest.json`：

```json
{
  "id": "com.example.my_lesson",
  "name": "我的知识点",
  "version": "1.0.0",
  "api": "1.0",
  "entry": "plugin.py",
  "class": "MyLessonPlugin",
  "category": { "id": "lesson", "label": "知识点讲解", "order": 10 },
  "dependencies": {},
  "requires_services": [],
  "provides_services": [],
  "subscribes": [],
  "publishes": [],
  "provides_extension_points": [],
  "contributes": {
    "main.content": [
      { "id": "com.example.my_lesson.panel", "title": "我的知识点", "category": "lesson" }
    ]
  }
}
```

3. 写 `plugin.py`：

```python
from sdk import Plugin, content_panel

class MyLessonPlugin(Plugin):
    def activate(self, context):
        context.extensions.contribute(
            "main.content",
            content_panel(
                "com.example.my_lesson.panel",
                "我的知识点",
                self._build,
                category="lesson",
                order=10,
            ),
        )

    def _build(self, parent):
        from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
        widget = QWidget(parent)
        QVBoxLayout(widget).addWidget(QLabel("这里放知识点内容", widget))
        return widget
```

4. 安装：GUI「插件管理… → 安装文件夹…」选这个目录，或
   `python tools/plugin_cli.py install <目录>`。
   左侧导航会自动出现对应分类；不需要改 `core/`、`ui/` 或 `run.py` 的任何一行。

> 想做**新分类**？只改 `category.id/label/order`，例如 `{"id":"quiz","label":"习题库","order":40}`，
> 导航立刻多一项。想做**实验室**类插件？在 factory 里用 `QPainter` 画交互画布（参考示例 C）。
> 需要多文件？用相对导入 `from . import helper`，加载器把插件目录当作包处理。

---

## 8. 安装 / 启用 / 禁用 / 卸载

**GUI**：工具栏「插件管理…」→ 表格（ID / 名称 / 分类 / 版本 / 状态 / 依赖说明）
+ 分类筛选 + 「安装文件夹…」「启用」「禁用」「卸载」「刷新」+ 内核日志窗格。
失败原因以弹窗与日志双通道给出。

**CLI**：

```bash
python tools/plugin_cli.py list [--category lesson|tool|lab]
python tools/plugin_cli.py install <插件文件夹>
python tools/plugin_cli.py enable   <插件ID>
python tools/plugin_cli.py disable  <插件ID>
python tools/plugin_cli.py uninstall <插件ID>
```

`list` 会打印分类、扩展点、内容贡献数、已注册服务、事件订阅数，便于直接核对回滚是否干净。

---

## 9. 示例插件

| 插件 | 分类 | 作用 |
| --- | --- | --- |
| `com.example.content_a` | `lesson` 知识点讲解 | 贡献 `main.content` 真实内容；注册 `com.example.content_a.api` 服务；订阅 `knowledge.refresh_request`、发布 `knowledge.updated` |
| `com.example.content_b` | `tool` 工具 | `dependencies: {A: ">=1.0.0"}`、`requires_services: [A 的服务]`；订阅 A 的事件、发布 `tool.sync_ack` 与刷新请求，验证依赖与双通道协作 |
| `com.example.lab_coordinate` | `lab` 实验室 | 原生 `QPainter` 绘制平面直角坐标系 + 滑块实时重绘抛物线；注册自定义扩展点 `lab.canvas.tools` 用于验证扩展点回滚 |

A 与 B 之间没有任何 `import`；B 只通过服务容器拿到 A 的状态对象，通过事件总线同步更新。

> 若先安装 B 再安装 A：B 会因"缺少依赖插件"被拒绝加载并标记 `failed`（这正是验收项之一）。
> 之后在管理界面点 B 的「启用」即可重试。

---

## 10. 测试与验收

```bash
python tools/verify.py
# 或： python -m unittest discover -s tests -v
```

`tests/test_kernel.py` 共 12 项，纯 Python、无显示器、无需 PySide6：

| # | 覆盖 |
| --- | --- |
| 01 | 空壳启动：0 插件 / 0 内容 / 0 服务 / 0 订阅 / 仅内置扩展点 |
| 02 | 安装 A 后 `main.content` 出现内容，服务与事件订阅生效 |
| 03 | 卸载 A 后完全恢复空壳，插件目录与 `sys.modules` 均清空 |
| 04 | B 缺 A 时拒绝加载并给出含依赖 ID 的明确提示，壳子不受影响 |
| 05 | A/B 通过事件总线与服务容器双向协作 |
| 06 | 禁用后事件/服务/内容/自定义扩展点/模块全部回滚；被依赖方停用被阻止 |
| 07 | 卸载被依赖方被阻止并列出依赖方 |
| 08 | `activate()` 抛异常的插件被隔离，其它插件正常 |
| 09 | 未在清单声明的订阅被拒绝且无残留 |
| 10 | 分类完全来自插件清单；`core/`/`ui/` 无业务硬编码；全项目无 Web 技术 |
| 11 | 重启后按拓扑序恢复启用集 |
| 12 | 依赖解析器：缺失依赖、循环依赖、拓扑顺序 |

真实界面请按 `tests/acceptance.md` 的清单逐条肉眼验收（含空壳、分类导航、坐标系绘制、协作按钮、回滚、卸载）。

本机实测：`python tools/verify.py` → **Ran 12 tests / OK / 验收结果: 全部通过**。

---

## 11. 常见问题

- **启动报"缺少 PySide6"**：执行 `pip install -r requirements.txt`。内核、CLI、测试不依赖它。
- **安装时提示清单非法**：检查 `id` 是否与目录名一致、`api` 是否为 `1.0`、`entry`/`class` 是否存在、`contributes` 元素是否都有 `id`。
- **插件状态是"加载失败"**：看管理界面日志或 `records[id].message`；常见原因是依赖缺失、所需服务未注册、运行期做了清单未声明的动作。
- **分类没出现**：分类只在插件清单里声明，且导航只展示**已启用**插件的分类；管理表格展示全部已安装插件的分类。
- **卸载被阻止**：先卸载/停用依赖它的插件，这是刻意设计，避免留下悬空依赖。
- **内容面板显示"渲染失败（已隔离）"**：`factory` 必须返回 `QWidget`；其异常不会拖垮壳子，原因会直接显示在面板里。
