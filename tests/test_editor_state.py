import unittest
from pathlib import Path

from core.models import PhotoInfo
from gui.presenters.editor_state import build_editor_panel_state
from services.models import WorkflowSession


class EditorStateTests(unittest.TestCase):
    def test_build_editor_panel_state_for_photo_source_with_no_source_selected(self) -> None:
        state = build_editor_panel_state(
            session=WorkflowSession(),
            selected_paths=[],
            using_photo_source=True,
            latitude_text="",
            longitude_text="",
        )

        self.assertEqual(state.source_summary, "Coordinates to Apply: Not set")
        self.assertEqual(state.destination_names, [])
        self.assertFalse(state.can_clear_source)
        self.assertFalse(state.can_apply)

    def test_build_editor_panel_state_for_photo_source_with_gps(self) -> None:
        source = Path("/tmp/source.jpg")
        destination = Path("/tmp/destination.jpg")
        state = build_editor_panel_state(
            session=WorkflowSession(
                source_photo_path=source,
                source_photo_info=PhotoInfo(
                    path=source,
                    file_type="JPG",
                    current_latitude=40.5,
                    current_longitude=-111.8,
                ),
            ),
            selected_paths=[source, destination],
            using_photo_source=True,
            latitude_text="",
            longitude_text="",
        )

        self.assertEqual(
            state.source_summary,
            "Coordinates to Apply: 40.500000, -111.800000",
        )
        self.assertEqual(state.destination_names, ["destination.jpg"])
        self.assertTrue(state.can_clear_source)
        self.assertTrue(state.can_apply)

    def test_build_editor_panel_state_for_manual_source_without_valid_coordinates(self) -> None:
        destination = Path("/tmp/destination.jpg")
        state = build_editor_panel_state(
            session=WorkflowSession(),
            selected_paths=[destination],
            using_photo_source=False,
            latitude_text="bad",
            longitude_text="still bad",
        )

        self.assertEqual(state.source_summary, "Coordinates to Apply: Not set")
        self.assertEqual(state.destination_names, ["destination.jpg"])
        self.assertFalse(state.can_apply)

    def test_build_editor_panel_state_for_manual_source_with_valid_coordinates(self) -> None:
        destination = Path("/tmp/destination.jpg")
        state = build_editor_panel_state(
            session=WorkflowSession(),
            selected_paths=[destination],
            using_photo_source=False,
            latitude_text="40.486325",
            longitude_text="-111.813415",
        )

        self.assertEqual(
            state.source_summary,
            "Coordinates to Apply: 40.486325, -111.813415",
        )
        self.assertEqual(state.destination_names, ["destination.jpg"])
        self.assertTrue(state.can_apply)


if __name__ == "__main__":
    unittest.main()
