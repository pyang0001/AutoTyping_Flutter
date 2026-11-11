import random
import unittest

from plan import (
    is_newline,
    read_unit,
    sample_mistake_length,
    should_mistake,
    wrong_character,
)


class PlanTests(unittest.TestCase):
    def test_mistakes_stay_off_at_frequency_zero_and_skip_whitespace(self):
        rng = random.Random(1)
        self.assertFalse(should_mistake(rng, 0, "a"))
        self.assertFalse(should_mistake(rng, 50, " "))
        self.assertFalse(should_mistake(rng, 50, "\n"))

    def test_mistake_length_stays_near_the_average(self):
        rng = random.Random(2)
        for _ in range(30):
            length = sample_mistake_length(rng, 3)
            self.assertGreaterEqual(length, 2)
            self.assertLessEqual(length, 4)
        self.assertEqual(sample_mistake_length(rng, 1), 1)

    def test_wrong_characters_keep_case(self):
        rng = random.Random(3)
        for _ in range(20):
            lower = wrong_character(rng, "a")
            upper = wrong_character(rng, "A")
            self.assertEqual(len(lower), 1)
            self.assertNotEqual(lower, "a")
            self.assertEqual(upper, upper.upper())
            self.assertNotEqual(upper.lower(), "a")

    def test_newline_pairs_are_one_typing_unit(self):
        self.assertEqual(read_unit("a\r\nb", 1), "\r\n")
        self.assertEqual(read_unit("ab", 0), "a")
        self.assertTrue(is_newline("\n"))


if __name__ == "__main__":
    unittest.main()
