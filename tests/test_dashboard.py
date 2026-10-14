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
