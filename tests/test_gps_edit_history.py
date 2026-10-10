import unittest
from pathlib import Path

from services.gps_edit_history import GpsEditHistory, PhotoListSnapshot

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

    def test_remembers_the_photo_list_with_the_edit(self) -> None:
        history = GpsEditHistory()
        snapshot = PhotoListSnapshot(paths=(FIRST, SECOND), selected=(FIRST,))

        history.record(
            before={FIRST: (None, None)},
            after={FIRST: (1.0, 2.0)},
            photo_list=snapshot,
        )
        history.mark_undone()

        # Still there for redo after an undo.
        self.assertEqual(history.photo_list, snapshot)

    def test_photo_list_is_replaced_and_cleared_with_the_edit(self) -> None:
        history = GpsEditHistory()
        history.record(
            before={FIRST: (None, None)},
            after={FIRST: (1.0, 2.0)},
            photo_list=PhotoListSnapshot(paths=(FIRST,)),
        )

        history.record(before={SECOND: (None, None)}, after={SECOND: (3.0, 4.0)})
        self.assertIsNone(history.photo_list)

        history.record(
            before={FIRST: (None, None)},
            after={FIRST: (1.0, 2.0)},
            photo_list=PhotoListSnapshot(paths=(FIRST,)),
        )
        history.clear()
        self.assertIsNone(history.photo_list)


class GpsEditHistoryBackupTests(unittest.TestCase):
    def test_remembers_the_backups_an_edit_made(self) -> None:
        history = GpsEditHistory()
        backup = Path("/tmp/a_original.jpg")
        history.record(before={Path("/tmp/a.jpg"): (1.0, 2.0)}, after={Path("/tmp/a.jpg"): (3.0, 4.0)}, backups=(backup,))

        self.assertEqual(history.backups, (backup,))
        history.set_backups(())
        self.assertEqual(history.backups, ())
        history.set_backups((backup,))
        history.clear()
        self.assertEqual(history.backups, ())

    def test_no_backups_kept_for_an_edit_that_changed_nothing(self) -> None:
        history = GpsEditHistory()
        history.record(before={}, after={}, backups=(Path("/tmp/a_original.jpg"),))

        self.assertEqual(history.backups, ())


if __name__ == "__main__":
    unittest.main()
