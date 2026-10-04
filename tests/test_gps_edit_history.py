import unittest
from pathlib import Path

from services.gps_edit_history import GpsEditHistory

FIRST = Path("/tmp/first.jpg")
SECOND = Path("/tmp/second.jpg")


class GpsEditHistoryTests(unittest.TestCase):
    def test_new_history_has_nothing_to_undo_or_redo(self) -> None:
        history = GpsEditHistory()

        self.assertFalse(history.can_undo)
        self.assertFalse(history.can_redo)
        self.assertEqual(history.undo_states(), {})
        self.assertEqual(history.redo_states(), {})

    def test_undo_then_redo_cycle(self) -> None:
        history = GpsEditHistory()
        history.record(
            before={FIRST: (None, None)},
            after={FIRST: (40.5, -111.8)},
        )

        self.assertTrue(history.can_undo)
        self.assertFalse(history.can_redo)
        self.assertEqual(history.undo_states(), {FIRST: (None, None)})

        history.mark_undone()
        self.assertFalse(history.can_undo)
        self.assertTrue(history.can_redo)
        self.assertEqual(history.redo_states(), {FIRST: (40.5, -111.8)})

        history.mark_redone()
        self.assertTrue(history.can_undo)
        self.assertFalse(history.can_redo)

    def test_record_keeps_only_files_in_both_states(self) -> None:
        history = GpsEditHistory()
        history.record(
            before={FIRST: (None, None), SECOND: (1.0, 2.0)},
            after={FIRST: (40.5, -111.8)},
        )

        self.assertEqual(history.undo_states(), {FIRST: (None, None)})

    def test_new_record_replaces_previous_edit(self) -> None:
        history = GpsEditHistory()
        history.record(before={FIRST: (None, None)}, after={FIRST: (1.0, 2.0)})
        history.mark_undone()

        history.record(before={SECOND: (None, None)}, after={SECOND: (3.0, 4.0)})

        self.assertTrue(history.can_undo)
        self.assertFalse(history.can_redo)
        self.assertEqual(history.undo_states(), {SECOND: (None, None)})

    def test_clear_forgets_the_edit(self) -> None:
        history = GpsEditHistory()
        history.record(before={FIRST: (None, None)}, after={FIRST: (1.0, 2.0)})

        history.clear()

        self.assertFalse(history.can_undo)
        self.assertFalse(history.can_redo)

    def test_returned_states_are_copies(self) -> None:
        history = GpsEditHistory()
        history.record(before={FIRST: (None, None)}, after={FIRST: (1.0, 2.0)})

        history.undo_states().clear()

        self.assertEqual(history.undo_states(), {FIRST: (None, None)})


if __name__ == "__main__":
    unittest.main()
