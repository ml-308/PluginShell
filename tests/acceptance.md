# 手动验收清单（GUI 与命令行）

> 自动化验收请优先执行 `python tools/verify.py`（纯 Python，不需要显示器和 PySide6）。
> 下面的清单用于在真实原生窗口里逐条肉眼确认。

## 0. 准备

```bash
pip install -r requirements.txt
python tools/plugin_cli.py list        # 应显示"已安装 0 个 / 已启用 0 个 / 内容贡献 0"
```

## 1. 空壳启动

```bash
python run.py
```

- [ ] 窗口标题为 `PluginShell · 原生插件壳子`
- [ ] 主区域只有一句 **「请安装插件」** 与一个「打开插件管理…」按钮，没有任何业务内容
- [ ] 左侧分类导航只有「全部 (0)」
- [ ] 状态栏显示"空壳状态"

## 2. 安装插件 A 后出现内容（知识点讲解分类）

在窗口点「插件管理…」→「安装文件夹…」→ 选择
`sample_plugins/com.example.content_a`；或用命令：

```bash
python tools/plugin_cli.py install sample_plugins/com.example.content_a
```

- [ ] 主区域出现「知识点讲解 · 二次函数」内容面板
- [ ] 左侧导航自动出现「知识点讲解 (1)」——分类来自插件清单，内核没有写死
- [ ] 点击面板按钮，下面文字变为「已发布 N 次知识点更新」
- [ ] 管理界面「状态」列为「已启用」

## 3. 安装 B（工具分类）验证依赖与通信

先**不装 A**，直接在空壳里装 B：

- [ ] 弹出「插件操作未成功」，提示包含「缺少依赖插件 com.example.content_a (>=1.0.0)」
- [ ] 管理界面里 B 显示「加载失败」，日志区有同样原因，壳子窗口仍正常

再装 A 与 B（顺序任意，B 会自动把 A 一起按拓扑序启用）：

```bash
python tools/plugin_cli.py install sample_plugins/com.example.content_a
python tools/plugin_cli.py install sample_plugins/com.example.content_b
python tools/plugin_cli.py install sample_plugins/com.example.lab_coordinate
```

- [ ] 左侧导航出现「知识点讲解 / 工具 / 实验室」三项（按清单 order 排序）
- [ ] 点「实验室」能看到原生绘制的平面直角坐标系，拖动滑块抛物线实时重绘
- [ ] 点插件 A 的「发布知识点更新」，B 的速记面板同步计数 +1（事件总线）
- [ ] 点 B 的「读取 A 的服务并向 A 请求刷新」，文字显示 A 服务返回的知识点（服务容器）
- [ ] 点某个分类，主区域只显示该分类的面板；点「全部」显示三个

## 4. 禁用后的副作用回滚

管理界面选中 B →「禁用」：

- [ ] B 的面板消失，其余面板还在，日志出现「已停用插件 …，事件/服务/内容/扩展点/模块均已回滚」
- [ ] 选中 A 点「禁用」应被拒绝，提示包含依赖方 B（若 B 已禁用则允许）
- [ ] 全部禁用后主区域回到「请安装插件」，左侧只剩「全部 (0)」

等价命令核对：

```bash
python tools/plugin_cli.py list
# 内容贡献: 0 / 已注册服务: （无） / 事件订阅数: 0 / 扩展点: main.content
```

## 5. 卸载 A 后恢复空壳

在**未安装 B**（或先卸载 B）的情况下：

- [ ] 卸载 A 后主区域内容消失，左侧分类归零
- [ ] `plugins/` 目录下对应文件夹被删除
- [ ] 若 B 仍安装着，卸载 A 会被阻止并提示「以下已安装插件依赖它 → com.example.content_b」

## 6. 故障隔离

把任一插件的 `plugin.py` 临时改成 `activate()` 里 `raise RuntimeError("boom")` 再安装：

- [ ] 管理界面显示「加载失败」与原因，壳子不退出，其它插件照常工作
- [ ] 该插件的事件/服务/内容/扩展点都没有残留（`list` 命令里订阅数为 0）

## 7. 无 Web 技术

- [ ] 全项目无 `.html` / `.css` / `.js` 文件，源码无 `WebView` / `QWebEngine` / `Electron`
- [ ] 所有界面都是 Qt 原生 QWidget / QPainter（`python tools/verify.py` 也会静态检查）
