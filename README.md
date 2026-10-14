# TaskDeck Skills

长任务的执行与监控台。显式调用 `$task-deck-skills`，让 agent 在组织后台执行的同时创建 HTML 监控入口，并持续保存检查点、批次结果和状态。

这是纯 skill 仓库：入口为 [SKILL.md](SKILL.md)，附带离线 HTML 模板和 Python 标准库渲染器，不包含常驻业务服务。业务 worker 由 agent 按实际任务创建或复用。

## 安装与调用

将本仓库作为 `task-deck-skills` 文件夹放入支持的 skills 目录。Codex 本机可在本仓库根目录创建符号链接（目标不存在时）：

```bash
mkdir -p "$HOME/.codex/skills"
ln -s "$PWD" "$HOME/.codex/skills/task-deck-skills"
```

本 skill 配置为显式调用，不会因为普通请求可能耗时而自动接管。

```text
使用 $task-deck-skills 处理这个长任务：按目录分批转换文件，
并发 3，保留原件。后台运行，在启动时给我 HTML 监控页。
```

## 预览模板

```bash
python3 scripts/render_dashboard.py --demo --output /tmp/task-deck-demo/index.html
```

生成的是带“演示数据”标识的独立 HTML，不会启动业务任务。真实任务用：

```bash
python3 scripts/render_dashboard.py \
  --state /path/to/run/status.json --output /path/to/run/index.html --watch 5
```

渲染监听器只刷新页面文件；worker 和状态采集仍须在后台独立运行。详细状态格式见 [状态契约](references/status-contract.md)。
