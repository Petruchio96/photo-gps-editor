import unittest
from pathlib import Path

from core.models import PhotoInfo
from gui.presenters.source_preview import build_source_preview_state
from services.models import WorkflowSession


class SourcePreviewStateTests(unittest.TestCase):
    def test_build_source_preview_state_for_empty_session(self) -> None:
        state = build_source_preview_state(WorkflowSession())

        self.assertTrue(state.is_empty)
        self.assertEqual(state.filename_text, "No source photo selected")
        self.assertEqual(state.gps_text, "Source GPS: Not loaded")
        self.assertFalse(state.has_gps)
        self.assertFalse(state.can_clear_source)

    def test_build_source_preview_state_for_source_with_gps(self) -> None:
        source = Path("/tmp/source.jpg")
        state = build_source_preview_state(
            WorkflowSession(
                source_photo_path=source,
                source_photo_info=PhotoInfo(
                    path=source,
                    file_type="JPG",
                    current_latitude=40.5,
                    current_longitude=-111.8,
                ),
            )
        )

        self.assertFalse(state.is_empty)
        self.assertEqual(state.filename_text, "source.jpg")
        self.assertEqual(state.gps_text, "Source GPS: 40.500000, -111.800000")
        self.assertTrue(state.has_gps)
        self.assertTrue(state.can_clear_source)

    def test_build_source_preview_state_for_source_without_gps(self) -> None:
        source = Path("/tmp/source.jpg")
        state = build_source_preview_state(
            WorkflowSession(
                source_photo_path=source,
                source_photo_info=PhotoInfo(path=source, file_type="JPG"),
            )
        )

        self.assertFalse(state.is_empty)
        self.assertEqual(state.filename_text, "source.jpg")
        self.assertEqual(state.gps_text, "Source GPS: Not found in this photo")
        self.assertFalse(state.has_gps)
        self.assertTrue(state.can_clear_source)


if __name__ == "__main__":
    unittest.main()
