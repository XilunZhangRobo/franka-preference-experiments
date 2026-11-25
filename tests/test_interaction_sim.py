"""Regression checks for selecting person feedback independent of the scripted key."""

import unittest

from visual_prefs.interaction_sim import PREFERENCES, prepare


class InteractionSimulation(unittest.TestCase):
    def test_personas_disagree_on_teaching_and_transfer_share_scope(self):
        for family in PREFERENCES:
            for phase in ("teach", "transfer", "exception"):
                with self.subTest(family=family, phase=phase):
                    trial = prepare(family, phase, 2)
                    a, b = [trial.expected(profile) for profile in ("standard", "reverse")]
                    self.assertEqual(a == b, phase == "exception")
                    if phase == "teach":
                        for letter in trial.choices:
                            self.assertEqual(set(trial.person_menu(letter)), {"accept", "change"})
                            self.assertNotEqual(
                                trial.expected_response("standard", letter),
                                trial.expected_response("reverse", letter),
                            )

    def test_mat_correction_only_returns_the_shelved_mat(self):
        trial = prepare("paused-work", "teach", 3)
        for letter, key in trial.choices.items():
            _, motions = trial._response(letter, "change")
            self.assertEqual([(m.item, m.target) for m in motions], [(key, trial._origin(key))])

    def test_receiving_hand_transfer_has_two_distinct_holders(self):
        trial = prepare("receiving-hand", "teach", 1)
        for letter, side in trial.choices.items():
            _, actions = trial._response(letter, "change")
            actors = [
                "human-left" if side == "left" else "human",
                "human" if side == "left" else "human-left",
            ]
            self.assertEqual([motion.actor for motion in actions], actors)
            self.assertEqual([motion.style for motion in actions], ["hold", "hold"])

    def test_report_timing_has_observable_button_press(self):
        trial = prepare("completion-update", "teach", 1)
        for letter, side in trial.choices.items():
            for response in ("accept", "change"):
                _, moves = trial._response(letter, response)
                last = moves[-1]
                immediate = (side == "now") == (response == "accept")
                self.assertEqual(last.item, "pencil" if immediate else "speaker")
                presses = [m for m in moves if m.item == "speaker"]
                self.assertEqual([m.style for m in presses], ["touch"])

    def test_lighting_scope_changes_standard_choice(self):
        for phase, key in (("transfer", "ceiling"), ("exception", "desk")):
            trial = prepare("lighting", phase, 1)
            self.assertEqual(trial.choices[trial.expected("standard")], key)
            if phase == "exception":
                self.assertIn("projection", trial.scene.props)
