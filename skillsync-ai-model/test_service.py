"""Automated test suite for SkillSync AI inference service."""

import math
import unittest
from uuid import uuid4

from starlette.testclient import TestClient

from main import app


class TestAIService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ready")
        self.assertTrue(data["models"]["classification"])
        self.assertTrue(data["models"]["reliability"])
        self.assertEqual(
            sorted(data["categories"]),
            ["Carpentry", "Electrical", "Plumbing", "Welding"],
        )
        self.assertEqual(len(data["reliability_features"]), 6)

    def test_classify_all_four_categories(self):
        samples = [
            ("Fix the leaking water pipe under kitchen sink", "Plumbing"),
            ("Rewire circuit breaker and fix bedroom lighting", "Electrical"),
            ("Build a custom wooden bookshelf and repair door", "Carpentry"),
            ("Weld broken iron gate hinge and metal railings", "Welding"),
        ]
        for prompt, expected_category in samples:
            with self.subTest(category=expected_category):
                res = self.client.post("/classify", json={"text": prompt})
                self.assertEqual(res.status_code, 200)
                json_data = res.json()
                self.assertEqual(json_data["category"], expected_category)

    def test_recommend_rejects_incompatible_feature_contract(self):
        response = self.client.post('/recommend', json={'workers': [], 'feature_version': 'unknown-contract'})
        self.assertEqual(response.status_code, 422)

    def test_classify_invalid_input(self):
        # Text too short
        res = self.client.post("/classify", json={"text": "x"})
        self.assertEqual(res.status_code, 422)

        # Empty body
        res = self.client.post("/classify", json={})
        self.assertEqual(res.status_code, 422)

    def test_reliability_nullable_history(self):
        # All null history (cold start)
        res = self.client.post(
            "/reliability",
            json={
                "completed_jobs_before": None,
                "cancellation_rate_before": None,
                "late_rate_before": None,
                "avg_response_minutes_before": None,
                "avg_rating_before": None,
                "complaint_rate_before": None,
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        prob = data["reliability_probability"]
        self.assertTrue(0.0 <= prob <= 1.0)
        self.assertTrue(0.0 <= data["reliability_percentage"] <= 100.0)
        self.assertTrue(data["cold_start"])
        self.assertEqual(len(data["imputed_features"]), 6)

    def test_reliability_with_history(self):
        res = self.client.post(
            "/reliability",
            json={
                "completed_jobs_before": 25,
                "cancellation_rate_before": 0.04,
                "late_rate_before": 0.02,
                "avg_response_minutes_before": 15.0,
                "avg_rating_before": 4.8,
                "complaint_rate_before": 0.0,
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["cold_start"])
        self.assertEqual(len(data["imputed_features"]), 0)
        self.assertGreaterEqual(data["reliability_probability"], 0.5)

    def test_recommend_uuid_and_ranking(self):
        worker1_id = str(uuid4())
        worker2_id = str(uuid4())
        worker3_id = str(uuid4())

        payload = {
            "top_k": 3,
            "workers": [
                {
                    "worker_id": worker1_id,
                    "name": "Novice Worker",
                    "experience_years": 1,
                    "completed_jobs": 2,
                    "rating": 3.0,
                    "available": True,
                    "completed_jobs_before": 2,
                    "avg_rating_before": 3.0,
                },
                {
                    "worker_id": worker2_id,
                    "name": "Veteran Worker",
                    "experience_years": 15,
                    "completed_jobs": 80,
                    "rating": 4.9,
                    "certified": True,
                    "available": True,
                    "completed_jobs_before": 80,
                    "cancellation_rate_before": 0.01,
                    "late_rate_before": 0.01,
                    "avg_response_minutes_before": 10.0,
                    "avg_rating_before": 4.9,
                    "complaint_rate_before": 0.0,
                },
                {
                    "worker_id": worker3_id,
                    "name": "Unavailable Worker",
                    "experience_years": 10,
                    "completed_jobs": 40,
                    "rating": 4.5,
                    "available": False,
                },
            ],
        }

        res = self.client.post("/recommend", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["recommendations"]), 3)

        # Veteran worker should rank higher than novice worker
        top_rec = data["recommendations"][0]
        self.assertEqual(top_rec["worker_id"], worker2_id)
        self.assertEqual(top_rec["skill_level"], "Highly Skilled")
        self.assertGreater(top_rec["recommendation_score"], data["recommendations"][1]["recommendation_score"])

        # Check metadata
        for rec in data["recommendations"]:
            self.assertTrue(0.0 <= rec["reliability_probability"] <= 1.0)
            self.assertTrue(0.0 <= rec["recommendation_score"] <= 100.0)
            self.assertIn("explanation", rec)
            self.assertIsInstance(rec["imputed_features"], list)

    def test_recommend_empty_workers(self):
        res = self.client.post("/recommend", json={"workers": [], "top_k": 5})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["recommendations"], [])
        self.assertEqual(data["total_candidates"], 0)

    def test_recommend_duplicate_worker_ids(self):
        duplicate_id = str(uuid4())
        payload = {
            "workers": [
                {
                    "worker_id": duplicate_id,
                    "name": "Worker 1",
                    "experience_years": 5,
                    "completed_jobs": 10,
                    "available": True,
                },
                {
                    "worker_id": duplicate_id,
                    "name": "Worker 2",
                    "experience_years": 3,
                    "completed_jobs": 5,
                    "available": True,
                },
            ]
        }
        res = self.client.post("/recommend", json=payload)
        self.assertEqual(res.status_code, 422)

    def test_recommend_invalid_inputs(self):
        # Negative experience
        res = self.client.post(
            "/recommend",
            json={
                "workers": [
                    {
                        "worker_id": "w1",
                        "name": "Invalid Worker",
                        "experience_years": -1,
                        "completed_jobs": 0,
                        "available": True,
                    }
                ]
            },
        )
        self.assertEqual(res.status_code, 422)

        # Rating out of bounds (> 5.0)
        res = self.client.post(
            "/recommend",
            json={
                "workers": [
                    {
                        "worker_id": "w1",
                        "name": "Invalid Worker",
                        "experience_years": 1,
                        "completed_jobs": 0,
                        "rating": 6.5,
                        "available": True,
                    }
                ]
            },
        )
        self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main()
