#!/usr/bin/env python3
"""Render an offline TaskDeck snapshot. This helper does not execute business jobs."""
import argparse
import datetime as dt
from decimal import Decimal
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUN_STATES = {'planned', 'running', 'paused', 'blocked', 'failed', 'completed', 'finished_with_issues'}


def timestamp(value):
    if value is None:
        return
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamps must include a timezone')


def count(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(name + ' must be a nonnegative integer')
    return value


def validate(data):
    if data.get('schema_version') != 1:
        raise ValueError('Expected schema_version=1')
    run = data['run']
    for key in ('id', 'title', 'host'):
        if not isinstance(run.get(key), str) or not run[key]:
            raise ValueError('run.' + key + ' is required')
    if run['state'] not in RUN_STATES:
        raise ValueError('Unknown run state')
    if count(run['concurrency'], 'concurrency') < 1:
        raise ValueError('concurrency must be positive')
    if count(run.get('stale_after_seconds', 90), 'stale_after_seconds') < 1:
        raise ValueError('stale_after_seconds must be positive')
    if not run.get('updated_at'):
        raise ValueError('run.updated_at is required')
    for key in ('updated_at', 'started_at', 'heartbeat_at'):
        timestamp(run.get(key))
    process = run.get('process', {})
    if process.get('alive') is not None and type(process['alive']) is not bool:
        raise ValueError('process.alive must be boolean or null')
    timestamp(process.get('verified_at'))
    seen, totals = set(), dict(total=0, succeeded=0, failed=0, review=0, active=0)
    known = bool(data['batches'])
    for batch in data['batches']:
        if not isinstance(batch.get('id'), str) or not batch['id'] or batch['id'] in seen:
            raise ValueError('Batch IDs must be nonempty and unique')
        seen.add(batch['id'])
        if not isinstance(batch.get('label'), str):
            raise ValueError('Batch label is required')
        if batch['state'] not in (RUN_STATES - {'planned'}) | {'queued'}:
            raise ValueError('Unknown batch state')
        for key in ('succeeded', 'failed', 'review', 'active'):
            totals[key] += count(batch[key], key)
        handled = batch['succeeded'] + batch['failed'] + batch['review']
        if batch['total'] is None:
            known = False
        else:
            totals['total'] += count(batch['total'], 'total')
            if handled + batch['active'] > batch['total']:
                raise ValueError('Committed outcomes plus active items exceed batch total')
        if batch['state'] in {'completed', 'finished_with_issues'}:
            if batch['total'] is None or handled != batch['total'] or batch['active']:
                raise ValueError('Finished batch still has unprocessed items')
            if batch['state'] == 'completed' and batch['failed'] + batch['review']:
                raise ValueError('Completed batch still has unresolved outcomes')
    totals['handled'] = totals['succeeded'] + totals['failed'] + totals['review']
    totals['remaining'] = totals['total'] - totals['handled'] if known else None
    if not known:
        totals['total'] = None
    if run['state'] in {'completed', 'finished_with_issues'}:
        if totals['remaining'] != 0 or totals['active']:
            raise ValueError('Finished run still has unknown or unprocessed scope')
        if run['state'] == 'completed' and (totals['failed'] + totals['review'] or run.get('verification', {}).get('passed') is not True):
            raise ValueError('Completion requires resolved outcomes and explicit verification')
    if run['state'] in {'planned', 'paused'} and totals['active']:
        raise ValueError('Planned or paused run cannot have active work')
    for key in ('throughput_per_hour', 'eta_seconds'):
        value = data.get('telemetry', {}).get(key)
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
            raise ValueError('Invalid telemetry: ' + key)
    for event in data.get('events', []):
        timestamp(event['at'])
        if not isinstance(event['message'], str):
            raise ValueError('Event message must be a string')
    return totals


def estimate_ai_services(data):
    services = data.get('ai_services')
    if services is None:
        return None
    if not isinstance(services, list):
        raise ValueError('ai_services must be an array or null')
    estimates = []
    for service in services:
        if not isinstance(service, dict):
            raise ValueError('Each ai_services entry must be an object')
        for key in ('provider', 'model'):
            if not isinstance(service.get(key), str) or not service[key].strip():
                raise ValueError('ai_services.' + key + ' is required')
        if service.get('currency') not in {'USD', 'CNY'}:
            raise ValueError('ai_services.currency must be USD or CNY')
        for key in ('input_tokens', 'output_tokens'):
            if service.get(key) is not None:
                count(service[key], 'ai_services.' + key)
        for key in ('input_per_million', 'output_per_million'):
            value = service.get(key)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError('Invalid ai_services rate: ' + key)
        keys = ('input_tokens', 'output_tokens', 'input_per_million', 'output_per_million')
        cost = None
        if all(service.get(key) is not None for key in keys):
            cost = str((Decimal(service['input_tokens']) * Decimal(str(service['input_per_million']))
                        + Decimal(service['output_tokens']) * Decimal(str(service['output_per_million']))) / Decimal(1000000))
        estimates.append(dict(service, estimated_cost=cost))
    return estimates


def render(data, output, refresh=15):
    totals = validate(data)
    payload = dict(data, totals=totals, ai_services=estimate_ai_services(data), refresh_seconds=refresh)
    # JSON inside script elements must not be able to terminate the element.
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = (ROOT / 'assets' / 'dashboard.html').read_text(encoding='utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + '.tmp')
    temporary.write_text(template.replace('__TASK_DECK_DATA__', encoded), encoding='utf-8')
    temporary.replace(output)


def demo():
    current = dt.datetime.now(dt.timezone.utc)
    stamp = lambda seconds: (current - dt.timedelta(seconds=seconds)).isoformat()
    batches = []
    for index, values in enumerate([
        ('输入清单核对', 'completed', 200, 200, 0, 0, 0),
        ('第一组 · 文档转换', 'completed', 200, 200, 0, 0, 0),
        ('第二组 · 文档转换', 'finished_with_issues', 200, 182, 6, 12, 0),
        ('第三组 · 文档转换', 'running', 200, 28, 6, 6, 5),
        ('第四组 · 文档转换', 'queued', 200, 0, 0, 0, 0),
    ]):
        label, state, total, succeeded, failed, review, active = values
        batches.append(dict(id='batch-' + str(index + 1).zfill(3), label=label, state=state, total=total,
                            succeeded=succeeded, failed=failed, review=review, active=active))
    return {'schema_version': 1, 'demo': True,
        'run': {'id': 'demo-document-pass', 'title': '文档批量转换', 'description': '按目录分批处理原始文档，保留原件、输出记录与可恢复检查点。',
            'state': 'running', 'host': 'demo-worker', 'concurrency': 5, 'started_at': stamp(2400), 'updated_at': stamp(2),
            'heartbeat_at': stamp(2), 'stale_after_seconds': 90, 'process': {'alive': None, 'verified_at': None}},
        'ai_services': [
            {'provider': '美国 API · 演示', 'model': '示例模型 US', 'currency': 'USD',
             'input_tokens': 1200000, 'output_tokens': 300000, 'input_per_million': 2, 'output_per_million': 8},
            {'provider': '中国 API · 演示', 'model': '示例模型 CN', 'currency': 'CNY',
             'input_tokens': 800000, 'output_tokens': 200000, 'input_per_million': 1, 'output_per_million': 2},
        ],
        'batches': batches, 'telemetry': {'throughput_per_hour': 960, 'eta_seconds': 1350},
        'events': [
            {'at': stamp(280), 'level': 'info', 'message': '第二组已提交检查点 · 200 件'},
            {'at': stamp(260), 'level': 'warning', 'message': '12 件文档缺少输入信息，已列入待处理清单'},
            {'at': stamp(220), 'level': 'info', 'message': '第三组开始处理 · 5 个并发工作单元'},
            {'at': stamp(12), 'level': 'info', 'message': '新增结果已保存，正在继续执行'},
        ], 'artifacts': []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--state', type=Path)
    source.add_argument('--demo', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--watch', type=float, default=0, help='Re-render every N seconds; not a worker supervisor')
    parser.add_argument('--refresh', type=int, default=15, help='Browser reload interval; 0 disables automatic reload')
    args = parser.parse_args()
    if args.watch < 0 or not math.isfinite(args.watch) or args.refresh < 0 or (args.demo and args.watch):
        parser.error('Use nonnegative intervals; --demo cannot be watched')
    if args.state and args.state.resolve() == args.output.resolve():
        parser.error('State and HTML output must use different paths')
    while True:
        try:
            data = demo() if args.demo else json.loads(args.state.read_text(encoding='utf-8'))
            render(data, args.output, args.refresh)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print('TaskDeck render error: ' + str(exc), file=sys.stderr, flush=True)
            if not args.watch:
                raise SystemExit(1)
        if not args.watch:
            print(str(args.output.resolve()))
            return
        time.sleep(args.watch)


if __name__ == '__main__':
    main()
