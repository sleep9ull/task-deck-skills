import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('dashboard', Path(__file__).resolve().parents[1] / 'scripts/render_dashboard.py')
dashboard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dashboard)


class DashboardTests(unittest.TestCase):
    def test_counts_are_derived_without_double_counting_active(self):
        totals = dashboard.validate(dashboard.demo())
        self.assertEqual((totals['handled'], totals['remaining'], totals['active']), (640, 360, 5))
        self.assertEqual(totals['handled'] + totals['remaining'], totals['total'])

    def test_unknown_scope_has_no_remaining_estimate(self):
        data = dashboard.demo()
        data['batches'][-1]['total'] = None
        totals = dashboard.validate(data)
        self.assertIsNone(totals['total'])
        self.assertIsNone(totals['remaining'])

    def test_invalid_counts_and_duplicate_ids_are_rejected(self):
        for mutate in (
            lambda d: d['batches'][0].update(succeeded=201),
            lambda d: d['batches'][0].update(succeeded=-1),
            lambda d: d['batches'][1].update(id=d['batches'][0]['id']),
            lambda d: d['run'].update(updated_at='2026-10-14T10:00:00'),
        ):
            with self.subTest(mutate=mutate):
                data = dashboard.demo()
                mutate(data)
                with self.assertRaises(ValueError):
                    dashboard.validate(data)

    def test_completed_requires_all_results_and_verification(self):
        data = dashboard.demo()
        data['run']['state'] = 'completed'
        with self.assertRaises(ValueError):
            dashboard.validate(data)
        for b in data['batches']:
            b.update(state='completed', succeeded=b['total'], failed=0, review=0, active=0)
        with self.assertRaises(ValueError):
            dashboard.validate(data)
        data['run']['verification'] = {'passed': True}
        self.assertEqual(dashboard.validate(data)['remaining'], 0)

    def test_invalid_snapshot_preserves_last_good_html(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'index.html'
            data = dashboard.demo()
            dashboard.render(data, path)
            before = path.read_bytes()
            data['batches'][0]['succeeded'] = -1
            with self.assertRaises(ValueError):
                dashboard.render(data, path)
            self.assertEqual(path.read_bytes(), before)

    def test_ai_costs_keep_currencies_and_decimal_precision(self):
        data = dashboard.demo()
        estimates = dashboard.estimate_ai_services(data)
        self.assertEqual([(s['currency'], s['estimated_cost']) for s in estimates],
                         [('USD', '4.8'), ('CNY', '1.2')])
        data['ai_services'][0].update(input_tokens=1, output_tokens=0, input_per_million=0.1)
        self.assertEqual(dashboard.estimate_ai_services(data)[0]['estimated_cost'], '1E-7')

    def test_ai_missing_empty_unknown_and_zero_are_distinct(self):
        self.assertIsNone(dashboard.estimate_ai_services({}))
        self.assertEqual(dashboard.estimate_ai_services({'ai_services': []}), [])
        data = dashboard.demo()
        data['ai_services'][0]['input_tokens'] = None
        self.assertIsNone(dashboard.estimate_ai_services(data)[0]['estimated_cost'])
        data['ai_services'][0].update(input_tokens=0, output_tokens=0)
        self.assertEqual(dashboard.estimate_ai_services(data)[0]['estimated_cost'], '0')

    def test_invalid_ai_values_preserve_last_good_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'index.html'
            dashboard.render(dashboard.demo(), path)
            before = path.read_bytes()
            for key, value in [('model', ''), ('provider', ' '), ('currency', 'EUR'),
                               ('input_tokens', -1), ('output_tokens', 1.5), ('input_tokens', True),
                               ('input_per_million', float('inf')), ('output_per_million', -1)]:
                with self.subTest(key=key, value=value):
                    data = dashboard.demo()
                    data['ai_services'][0][key] = value
                    with self.assertRaises(ValueError):
                        dashboard.render(data, path)
                    self.assertEqual(path.read_bytes(), before)

    def test_untrusted_text_cannot_close_embedded_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'index.html'
            data = copy.deepcopy(dashboard.demo())
            data['run']['title'] = '</script><script>window.INJECTED=true</script>'
            dashboard.render(data, path)
            output = path.read_text()
            self.assertNotIn(data['run']['title'], output)
            self.assertIn('\\u003c/script\\u003e', output)


if __name__ == '__main__':
    unittest.main()
