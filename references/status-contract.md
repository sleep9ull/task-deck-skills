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

## 外部 AI API 预估

可选 `ai_services` 按服务及模型记录**全任务预计总消耗**（含预计重试），不是累计实际用量。未提供或 `null` 表示尚未估算；`[]` 明确表示无需外部 AI API。已有状态文件可继续使用。

```json
"ai_services": [
  {"provider": "服务商名称", "model": "实际模型 ID", "currency": "USD",
   "input_tokens": 1200000, "output_tokens": 300000,
   "input_per_million": 2, "output_per_million": 8}
]
```

以上数值仅演示结构，不代表任何模型的实际价格。`provider` 与 `model` 必须为非空字符串；美国 API 使用 `USD`，中国模型使用 `CNY`，按实际服务填写，不能仅凭模型名称猜测。不同币种不换算、不合计。

两个 token 字段为非负整数或 `null`；两个单价字段为非负有限数或 `null`，单位为对应币种 / 百万 token。缺失字段按未知处理，零仅用于确定为零的用量或免费单价。渲染器计算 `(输入 token × 输入单价 + 输出 token × 输出单价) / 1,000,000`；任一项未知则成本显示“待估算”。

适配器在启动前根据任务范围、试跑样本和服务商当前报价填写预估，并在计划变化时更新。在 `plan.json` 保存报价来源、核验时间及估算依据；有缓存、分层计价时使用有依据的有效单价，无法可靠估算则保留未知。此表仅估算 token 费用，不含图片、音频等其他计费项目，也不代表已获付费调用授权。

## 事件与链接

`events`：近期窗口，最多展示最后 50 条，字段 `at`、`level`（info/warning/error）、`message`。完整事件在运行目录追加保存。

`artifacts`：`{"label":"结果清单","path":"results.jsonl"}`。batch.result_path 与 verification.evidence_path 同样为相对 HTML 的本运行目录内路径。模板拒绝协议 URL、绝对路径和 `..` 跳转；将对外共享的输出放入可访问的运行目录。

生产状态默认不含 demo。演示样例须明确 `demo=true`；它只能用于模板预览，不能充当真实后台任务的证据。
