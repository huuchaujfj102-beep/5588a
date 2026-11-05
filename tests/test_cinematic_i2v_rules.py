import unittest

from oneflow.cinematic_i2v_rules import (
    TEMPORAL_PREFIX, TEMPORAL_NEGATIVE_LAYERS,
    apply_temporal_rules, build_temporal_negative, source_frame_gate
)
from oneflow.director import film_prompt


class CinematicI2VRulesTests(unittest.TestCase):
    def test_director_prompt_is_prefixed(self):
        result = film_prompt("a vehicle runs", "accelerating", "starting", 1, 3)
        self.assertTrue(result.startswith(TEMPORAL_PREFIX))
        self.assertIn("1. Original image/asset lock:", result)
        self.assertIn("7. Negative constraints:", result)

    def test_temporal_prefix_idempotence(self):
        self.assertEqual(apply_temporal_rules(apply_temporal_rules("moving car")),
                         apply_temporal_rules("moving car"))

    def test_empty_prompt_fails(self):
        with self.assertRaises(ValueError):
            apply_temporal_rules(" ")

    def test_temporal_negative_plain(self):
        plain = build_temporal_negative()
        self.assertIn(TEMPORAL_NEGATIVE_LAYERS["A"], plain)
        self.assertNotIn(":1.4", plain)

    def test_temporal_negative_weighted_explicit(self):
        weighted = build_temporal_negative(weighted=True)
        self.assertIn(":1.4)", weighted)
        self.assertIn(":1.2)", weighted)

    def test_temporal_negative_exclusion(self):
        no_c = build_temporal_negative(exclude_layers=("C",))
        self.assertNotIn(TEMPORAL_NEGATIVE_LAYERS["C"], no_c)
        with self.assertRaises(ValueError):
            build_temporal_negative(exclude_layers=("D",))

    def test_reference_gate_requires_human_pass(self):
        for status in ("PENDING", "REVIEW_REQUIRED", "FAIL", None, "PASS"):
            with self.subTest(status=status):
                with self.assertRaises(ValueError):
                    source_frame_gate(status)
        self.assertTrue(source_frame_gate("PASS_HUMAN"))


if __name__ == "__main__":
    unittest.main()
