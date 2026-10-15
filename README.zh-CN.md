# TaskDeck Skills

[![English](https://img.shields.io/badge/English-switch_language-64748b?style=for-the-badge)](README.md) [![简体中文](https://img.shields.io/badge/简体中文-当前语言-2563eb?style=for-the-badge)](README.zh-CN.md)

用于后台执行长任务、同步提供实时 HTML 进度监控页的 agent skill。显式调用 `$task-deck-skills`，让 agent 规划批次、保存检查点、记录结果，并从任务启动时就展示进度。

适用于批量处理、数据采集、迁移、生成和分析。本仓库包含 [skill 指令](SKILL.md)、离线 HTML 模板和基于 Python 标准库的渲染器。业务 worker 由 agent 按实际任务创建或复用。

## 安装 TaskDeck

将本仓库克隆到支持的 skills 目录，或为已有仓库创建链接。Codex 本机可在本仓库根目录运行以下命令，前提是目标路径尚不存在：

```bash
mkdir -p "$HOME/.codex/skills"
ln -s "$PWD" "$HOME/.codex/skills/task-deck-skills"
```

使用符号链接期间，请保留仓库所在位置。渲染监控页需要 Python 3，无需第三方 Python 包或 Web 服务器。

## 使用 TaskDeck

在 Codex 中显式调用 `$task-deck-skills`，说明任务、约束和预期产物：

```text
使用 $task-deck-skills 处理这个长任务：按目录分批转换文件，
并发 3，保留原件。后台运行，在启动时给我 HTML 监控页。
```

本 skill 配置为显式调用，不会因为普通请求可能耗时而自动接管。

## TaskDeck 能做什么

- 规划具有稳定 ID 的批次，明确范围和验收条件。
- 在执行前创建监控页，随后根据已保存的状态持续更新。
- 指导可恢复的后台执行，保存检查点、日志并核验进程。
- 分别记录成功、失败和待人工处理的项目，支持批次搜索与结果链接。
- 核验产物，保留包含结果和未解决问题的最终快照。

监控页展示已记录的状态。渲染器不负责执行业务 worker 或采集其状态；这些进程须在后台独立运行。

## 预览监控页

在本仓库根目录生成独立 HTML 预览：

```bash
python3 scripts/render_dashboard.py --demo --output /tmp/task-deck-demo/index.html
```

在浏览器中打开 `/tmp/task-deck-demo/index.html`。页面带有“演示数据”标识，不会启动业务任务。

对于真实任务，读取已有状态文件，每五秒刷新 HTML 文件：

```bash
python3 scripts/render_dashboard.py \
  --state /path/to/run/status.json --output /path/to/run/index.html --watch 5
```

将示例路径替换为实际运行目录。生成的 HTML 可以直接在浏览器中打开，支持离线查看，无需开发服务器或 CDN。

## 参考文档

- [Skill 指令](SKILL.md)：规划、执行、监督与交付。
- [状态契约](references/status-contract.md)：状态格式、进度计数，以及可选的 AI token 与费用估算。
- [后台运行与恢复](references/execution.md)：worker、检查点与断点续跑。
- [界面规范](references/interface.md)：监控页布局与真实状态展示。

Skill 指令和参考文档目前使用中文编写。
