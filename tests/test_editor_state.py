import unittest
from pathlib import Path

from core.models import PhotoInfo
from gui.presenters.editor_state import build_editor_panel_state
from services.models import WorkflowSession


class EditorStateTests(unittest.TestCase):
    def test_build_editor_panel_state_for_photo_source_with_no_source_selected(self) -> None:
        state = build_editor_panel_state(
            session=WorkflowSession(),
            browser_selected_paths=[],
            target_selected_paths=[],
            using_photo_source=True,
            latitude_text="",
            longitude_text="",
        )

        self.assertEqual(state.source_summary, "Source GPS Coordinates: Not set")
        self.assertEqual(state.selected_photo_names, [])
        self.assertEqual(state.selected_photo_count, 0)
        self.assertEqual(state.selected_gps_count, 0)
        self.assertFalse(state.can_clear_source)
        self.assertFalse(state.can_apply)
        self.assertEqual(state.apply_tone, "safe")

    def test_build_editor_panel_state_for_photo_source_with_gps(self) -> None:
        source = Path("/tmp/source.jpg")
        target_photo = Path("/tmp/target-photo.jpg")
        state = build_editor_panel_state(
            session=WorkflowSession(
                target_paths=[source, target_photo],
                source_photo_path=source,
                source_photo_info=PhotoInfo(
                    path=source,
                    file_type="JPG",
                    current_latitude=40.5,
                    current_longitude=-111.8,
                ),
            ),
            browser_selected_paths=[],
            target_selected_paths=[],
            using_photo_source=True,
            latitude_text="",
            longitude_text="",
        )

        self.assertEqual(
            state.source_summary,
            "Source GPS Coordinates: 40.500000, -111.800000",
        )
        self.assertEqual(state.selected_photo_names, ["target-photo.jpg"])
        self.assertEqual(state.selected_photo_count, 1)
        self.assertEqual(state.selected_gps_count, 0)
        self.assertTrue(state.can_clear_source)
        self.assertTrue(state.can_apply)
        self.assertEqual(state.apply_tone, "safe")

    def test_build_editor_panel_state_for_manual_source_without_valid_coordinates(self) -> None:
        target_photo = Path("/tmp/target-photo.jpg")
        state = build_editor_panel_state(
            session=WorkflowSession(target_paths=[target_photo]),
            browser_selected_paths=[],
            target_selected_paths=[],
            using_photo_source=False,
            latitude_text="bad",
            longitude_text="still bad",
        )

        self.assertEqual(state.source_summary, "Source GPS Coordinates: Not set")
        self.assertEqual(state.selected_photo_names, ["target-photo.jpg"])
        self.assertEqual(state.selected_photo_count, 1)
        self.assertEqual(state.selected_gps_count, 0)
        self.assertFalse(state.can_apply)
        self.assertEqual(state.apply_tone, "safe")

    def test_build_editor_panel_state_for_manual_source_with_valid_coordinates(self) -> None:
        target_photo = Path("/tmp/target-photo.jpg")
        state = build_editor_panel_state(
            session=WorkflowSession(target_paths=[target_photo]),
            browser_selected_paths=[],
            target_selected_paths=[],
            using_photo_source=False,
            latitude_text="40.486325",
            longitude_text="-111.813415",
        )

        self.assertEqual(
            state.source_summary,
            "Source GPS Coordinates: 40.486325, -111.813415",
        )
        self.assertEqual(state.selected_photo_names, ["target-photo.jpg"])
        self.assertEqual(state.selected_photo_count, 1)
        self.assertEqual(state.selected_gps_count, 0)
        self.assertTrue(state.can_apply)
        self.assertEqual(state.apply_tone, "safe")

    def test_build_editor_panel_state_marks_warning_when_target_already_has_gps(self) -> None:
        target_photo = Path("/tmp/target-photo.jpg")
        state = build_editor_panel_state(
            session=WorkflowSession(
                target_paths=[target_photo],
                loaded_photo_infos={
                    target_photo: PhotoInfo(
                        path=target_photo,
                        file_type="JPG",
                        current_latitude=40.5,
                        current_longitude=-111.8,
                    )
                }
            ),
            browser_selected_paths=[],
            target_selected_paths=[target_photo],
            using_photo_source=False,
            latitude_text="40.486325",
            longitude_text="-111.813415",
        )

        self.assertTrue(state.can_apply)
        self.assertEqual(state.apply_tone, "warning")
        self.assertTrue(state.can_clear_list_gps)
        self.assertEqual(state.selected_photo_count, 1)
        self.assertEqual(state.selected_gps_count, 1)


if __name__ == "__main__":
    unittest.main()
