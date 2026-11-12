import random
import unittest

from engine import VERSION, TyperEngine, focus_action, settings_problems
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
        self.assertEqual(sample_mistake_length(rng, 0), 0)

    def test_wrong_characters_keep_case(self):
        rng = random.Random(3)
        for _ in range(20):
            lower = wrong_character(rng, "a")
            upper = wrong_character(rng, "A")
            self.assertEqual(len(lower), 1)
            self.assertNotEqual(lower, "a")
            self.assertEqual(upper, upper.upper())
            self.assertNotEqual(upper.lower(), "a")

    def test_settings_reject_values_outside_the_allowed_sets(self):
        valid = {
            "start_delay": 2,
            "default_speed": 30,
            "mistake_frequency": 0,
            "mistake_length": 5,
            "start_hotkey": "Ctrl+Up",
            "reset_hotkey": "Ctrl+Down",
        }
        self.assertEqual(settings_problems(valid), [])
        problems = " ".join(
            settings_problems(
                {
                    "start_delay": 4,
                    "default_speed": 31,
                    "mistake_frequency": 11,
                    "mistake_length": "a",
                    "start_hotkey": "s",
                    "reset_hotkey": "Down",
                }
            )
        )
        self.assertIn("1, 2, or 3", problems)
        self.assertIn("1 to 30", problems)
        self.assertIn("0 to 10", problems)
        self.assertIn("0 to 5", problems)
        self.assertIn("not a single character", problems)

    def test_typed_prefix_stays_when_the_rest_is_edited(self):
        engine = TyperEngine()
        engine.set_text("Hello world")
        engine.phase = "paused"
        engine.set_index(6)
        engine.set_text("Hello there", 6)
        self.assertEqual(engine.text, "Hello there")
        self.assertEqual(engine.index, 6)
        engine.set_text("Yello there", 6)
        self.assertEqual(engine.text, "Hello there")
        self.assertEqual(engine.index, 6)
        engine.phase = "typing"
        engine.set_text("Hello people", 6)
        self.assertEqual(engine.text, "Hello there")

    def test_cursor_marks_typed_letters_and_can_move(self):
        engine = TyperEngine()
        engine.set_text("Hello")
        engine.set_index(5)
        self.assertEqual(engine.index, 5)
        self.assertEqual(engine.phase, "ready")
        engine.set_index(2)
        self.assertEqual(engine.snapshot()["index"], 2)
        self.assertEqual(engine.phase, "paused")
        engine.phase = "done"
        engine.set_index(2)
        self.assertEqual(engine.phase, "paused")
        engine.set_index(0)
        self.assertEqual(engine.phase, "ready")
        engine.phase = "paused"
        engine.set_index(99)
        self.assertEqual(engine.index, 5)
        self.assertEqual(engine.phase, "done")

    def test_changing_speed_does_not_stop_the_run(self):
        engine = TyperEngine()
        engine.phase = "typing"
        engine.set_speed(18)
        self.assertEqual(engine.phase, "typing")
        self.assertEqual(engine.speed, 18)
        self.assertTrue(engine._speed_is_live())
        engine.set_speed(12, dragging=True)
        self.assertTrue(engine._speed_drag)
        self.assertEqual(engine.phase, "typing")
        engine.set_speed(12, dragging=False)
        self.assertFalse(engine._speed_drag)
        self.assertEqual(engine.phase, "typing")
        self.assertEqual(focus_action(True, 5, 9, True), "restore")
        self.assertEqual(focus_action(True, 5, 9, False), "pause")
        self.assertEqual(focus_action(False, 9, 9, False), "type")
        self.assertEqual(focus_action(False, 4, 9, True), "pause")

    def test_first_release_reports_its_version(self):
        self.assertEqual(VERSION, "1.0.0")
        self.assertEqual(TyperEngine().snapshot()["version"], "1.0.0")

    def test_mistyped_letters_are_reported_until_the_run_stops(self):
        engine = TyperEngine()
        engine.text = "Hello"
        engine.index = 1
        engine.phase = "typing"
        engine._typo = "x"
        self.assertEqual(engine.snapshot()["typo"], "x")
        engine.phase = "paused"
        self.assertEqual(engine.snapshot()["typo"], "")

    def test_newline_pairs_are_one_typing_unit(self):
        self.assertEqual(read_unit("a\r\nb", 1), "\r\n")
        self.assertEqual(read_unit("ab", 0), "a")
        self.assertTrue(is_newline("\n"))


if __name__ == "__main__":
    unittest.main()
