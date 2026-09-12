import unittest

import numpy as np
from hiershrink_swe_compare import matched_random, select_threshold


class ComparisonTest(unittest.TestCase):
    def test_budget_selects_useful_upgrade(self):
        scores = np.array([0.8, 0.2, 0.1])
        quality = np.array([[0, 1], [1, 0], [1, 1]])
        costs = np.array([[1, 3], [1, 3], [1, 3]])
        threshold = select_threshold(scores, quality, costs, 5 / 3)
        np.testing.assert_array_equal(scores >= threshold, [True, False, False])
        with self.assertRaises(ValueError):
            select_threshold(scores, quality, costs, 0.5)

    def test_random_matches_expected_cost_without_clipping(self):
        quality = np.array([[0, 1], [1, 0]])
        costs = np.array([[1, 3], [1, 3]])
        np.testing.assert_array_equal(matched_random(quality, costs, 1.5), [0.25, 0.75])
        self.assertIsNone(matched_random(quality, costs, 4))


if __name__ == "__main__":
    unittest.main()
