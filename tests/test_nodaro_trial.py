import unittest
from unittest.mock import patch
from oneflow import nodaro_trial as n


class NodaroTrialTests(unittest.TestCase):
    def test_film_plan_is_real_14_second_sequence(self):
        p = n.plan()
        self.assertEqual(p["duration"], 14)
        self.assertEqual([s["seconds"] for s in p["shots"]], [4, 4, 4, 2])
        self.assertEqual([s["start"] for s in p["shots"]], [0, 4, 8, 12])
        self.assertFalse(p["publish_approved"])
        self.assertEqual(set(s["resolution"] for s in p["shots"]), {"480p"})
        for shot in p["shots"]:
            self.assertIn("exact same", shot["prompt"].lower())

    def test_unknown_quote_fails_closed(self):
        with patch.object(n, "api", return_value={"data": {"nonsensical": 88}}):
            with self.assertRaises(n.Blocked):
                n.quote("fake", "fake")
        with patch.object(n, "api", return_value={"data": {"credits": 42}}):
            self.assertEqual(n.quote("fake", "id"), 42)

    def test_balance_unparseable_fails_closed(self):
        with patch.object(n, "api", return_value={"data": {"tier": "free"}}):
            with self.assertRaises(n.Blocked):
                n.balance("fake")


if __name__ == "__main__":
    unittest.main()
