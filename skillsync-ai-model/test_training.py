import copy
from datetime import UTC, datetime, timedelta
import hashlib
import unittest
from train_from_outcomes import CONTRACT, FEATURES, ROOT, prepare, train_candidate


def sample():
    rows = []
    for index in range(120):
        timestamp = datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=index)
        rows.append({'booking_id': str(index), 'worker_id': str(index % 6), 'category': 'Plumbing',
                     'data_source': 'real', 'feature_version': CONTRACT['version'],
                     'predicted_at': timestamp.isoformat(), 'outcome_at': (timestamp + timedelta(hours=1)).isoformat(),
                     'completed_jobs_before': index // 6, 'cancellation_rate_before': .1,
                     'late_rate_before': .2, 'avg_response_minutes_before': None,
                     'avg_rating_before': 4, 'complaint_rate_before': 0,
                     'completed_on_time': index % 2})
    return {'featureVersion': CONTRACT['version'], 'target': CONTRACT['target'], 'rows': rows}


class TrainingTests(unittest.TestCase):
    def test_rejects_insufficient_demo_duplicate_and_mismatched_data(self):
        for modify in (lambda p: p.update(rows=[]),
                       lambda p: p['rows'][0].update(data_source='test'),
                       lambda p: p['rows'][0].update(booking_id='1'),
                       lambda p: p.update(featureVersion='legacy'),
                       lambda p: p['rows'][0].update(cancellation_rate_before=2)):
            payload = sample()
            modify(payload)
            with self.assertRaises(ValueError):
                prepare(payload)

    def test_time_split_purges_outcomes_unknown_at_cutoff(self):
        payload = sample()
        payload['rows'][0]['outcome_at'] = payload['rows'][-1]['outcome_at']
        train, test, cutoff = prepare(payload)
        self.assertTrue((train.observed < cutoff).all())
        self.assertTrue((train.captured < test.captured.min()).all())
        self.assertNotIn('0', train.booking_id.tolist())

    def test_candidate_training_compares_baseline_without_modifying_it(self):
        baseline = ROOT / 'models/reliability_rf.joblib'
        digest = hashlib.sha256(baseline.read_bytes()).hexdigest()
        candidate, report = train_candidate(sample(), baseline)
        self.assertEqual(list(candidate.feature_names_in_), FEATURES)
        self.assertEqual(report['trainRows'], 96)
        self.assertEqual(report['testRows'], 24)
        self.assertIn('brierScore', report['candidate'])
        self.assertIn('calibration', report['baseline'])
        self.assertEqual(hashlib.sha256(baseline.read_bytes()).hexdigest(), digest)


if __name__ == '__main__':
    unittest.main()
