# status.json 契约

适配器从持久化检查点生成该文件；先写同目录临时文件，再原子替换。字段不包含凭据、Cookie 或完整浏览器配置。渲染器使用 Python 3.9+ 标准库。

```json
{
  "schema_version": 1,
  "run": {
    "id": "run-001",
    "title": "素材批量处理",
    "description": "按目录分批处理，保留原件与逐件结果。",
    "state": "planned",
    "host": "worker-host",
    "concurrency": 3,
    "started_at": null,
    "updated_at": "2026-10-14T09:00:00Z",
    "heartbeat_at": null,
    "stale_after_seconds": 90,
    "process": {"alive": null, "verified_at": null},
    "verification": {"passed": false, "evidence_path": null}
  },
  "batches": [
    {"id": "batch-001", "label": "目录 A", "state": "queued", "total": 20,
     "succeeded": 0, "failed": 0, "review": 0, "active": 0, "result_path": null}
  ],
  "events": [],
  "artifacts": []
}
```

## 状态与计数

- run.state：`planned`、`running`、`paused`、`blocked`、`failed`、`completed`、`finished_with_issues`。
- batch.state：同上，尚未执行用 `queued` 替代 `planned`。批次 `failed` 表示执行故障；不把未尝试条目加到 failed 计数。
- total 是条目数，未知时填 `null`。succeeded / failed / review 是互斥的最新已提交条目结果；重试次数另计，不重复计入条目总数。
- 已处理 = succeeded + failed + review；尚未处理 = total − 已处理。active 是尚未处理的子集，不再次加入分母。render 从 batches 求和，不接收第二套全局计数。
- `review` 包括需人工处理或被跳过的条目；具体原因放在事件和结果中。保留未知总量，不显示虚假的百分比/剩余数。
- completed 要求总量已知、无剩余/在途/失败/待处理，且 run.verification.passed=true。finished_with_issues 要求已无剩余/在途，但仍有明确缺口；该状态不自动代表用户目标已满足。

时间字段使用带时区 ISO 8601。`updated_at` 是业务状态快照时间；`heartbeat_at` 是执行器最后心跳；`process.verified_at` 是真实进程/作业核验时间。远端查询失败时 alive=null，不将其改为 false。alive=false 只用于明确终止的观察。

running 同时具有新鲜心跳、alive=true 和新鲜进程核验时，页面才显示“执行中”；否则显示“状态待核验”。页面不把渲染时间当 worker 心跳。planned/paused/blocked/终态保持其明确标签，同时展示快照时间。

可选 `telemetry`：`throughput_per_hour`、`eta_seconds`，非负数或 null。由实际工作窗口测量；未知时显示“—”。只允许在运行且状态新鲜时显示 ETA。

## 事件与链接

`events`：近期窗口，最多展示最后 50 条，字段 `at`、`level`（info/warning/error）、`message`。完整事件在运行目录追加保存。

`artifacts`：`{"label":"结果清单","path":"results.jsonl"}`。batch.result_path 与 verification.evidence_path 同样为相对 HTML 的本运行目录内路径。模板拒绝协议 URL、绝对路径和 `..` 跳转；将对外共享的输出放入可访问的运行目录。

生产状态默认不含 demo。演示样例须明确 `demo=true`；它只能用于模板预览，不能充当真实后台任务的证据。
