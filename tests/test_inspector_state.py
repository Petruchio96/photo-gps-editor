import unittest
from pathlib import Path

from core.models import GpsCoordinates, PhotoInfo
from gui.presenters.inspector_state import build_inspector_state

WITH_GPS = Path("/tmp/with-gps.jpg")
NO_GPS = Path("/tmp/no-gps.jpg")
OTHER_NO_GPS = Path("/tmp/other.jpg")

INFOS = {
    WITH_GPS: PhotoInfo(WITH_GPS, "JPG", 40.5, -111.8),
    NO_GPS: PhotoInfo(NO_GPS, "JPG"),
    OTHER_NO_GPS: PhotoInfo(OTHER_NO_GPS, "JPG"),
}


def state(selected, latitude="", longitude=""):
    return build_inspector_state(
        selected_paths=list(selected),
        photo_infos=INFOS,
        latitude_text=latitude,
        longitude_text=longitude,
    )


class InspectorStateTests(unittest.TestCase):
    def test_nothing_selected(self) -> None:
        result = state([])

        self.assertEqual(result.title, "No Photos Selected")
        self.assertFalse(result.can_apply)
        self.assertEqual(result.apply_label, "Apply to Selected Photos")
        self.assertEqual(result.apply_hint, "Select the photos to update in the grid.")
        self.assertFalse(result.can_remove_gps)
        self.assertEqual(result.remove_gps_label, "Remove GPS")

    def test_single_photo_with_gps(self) -> None:
        result = state([WITH_GPS])

        self.assertEqual(result.title, "with-gps.jpg")
        self.assertEqual(result.gps_summary, "Current GPS: 40.500000, -111.800000")
        self.assertEqual(result.single_photo_coordinates, GpsCoordinates(40.5, -111.8))
        self.assertTrue(result.can_use_location)
        self.assertEqual(result.remove_gps_label, "Remove GPS from 1 Photo")

    def test_single_photo_without_gps(self) -> None:
        result = state([NO_GPS])

        self.assertEqual(result.gps_summary, "Current GPS: none")
        self.assertFalse(result.can_use_location)
        self.assertFalse(result.can_remove_gps)

    def test_multiple_photos_gps_summary(self) -> None:
        self.assertEqual(
            state([WITH_GPS, NO_GPS]).gps_summary,
            "Current GPS: 1 of 2 have GPS",
        )
        self.assertEqual(
            state([NO_GPS, OTHER_NO_GPS]).gps_summary,
            "Current GPS: none of them have GPS",
        )
        self.assertEqual(state([WITH_GPS]).title, "with-gps.jpg")
        self.assertEqual(state([NO_GPS, OTHER_NO_GPS]).title, "2 Photos Selected")

    def test_needs_location_before_apply(self) -> None:
        result = state([NO_GPS])

        self.assertFalse(result.can_apply)
        self.assertEqual(result.apply_hint_tone, "info")
        self.assertIn("Set a new location", result.apply_hint)

    def test_invalid_location_is_an_error(self) -> None:
        result = state([NO_GPS], "95", "10")

        self.assertFalse(result.can_apply)
        self.assertIsNone(result.new_location)
        self.assertEqual(result.apply_hint_tone, "error")

    def test_ready_to_apply(self) -> None:
        result = state([NO_GPS, OTHER_NO_GPS], "40.1", "-111.2")

        self.assertTrue(result.can_apply)
        self.assertEqual(result.apply_label, "Apply to 2 Photos")
        self.assertEqual(result.new_location, GpsCoordinates(40.1, -111.2))
        self.assertEqual(result.apply_hint, "")
        self.assertEqual(result.overwrite_count, 0)

    def test_overwrite_warning(self) -> None:
        result = state([WITH_GPS, NO_GPS], "40.1", "-111.2")

        self.assertTrue(result.can_apply)
        self.assertEqual(result.overwrite_count, 1)
        self.assertEqual(result.apply_hint, "1 photo already has GPS, which will be replaced.")
        self.assertEqual(result.apply_hint_tone, "warning")

    def test_overwrite_warning_plural(self) -> None:
        infos = dict(INFOS)
        second = Path("/tmp/second-gps.jpg")
        infos[second] = PhotoInfo(second, "JPG", 1.0, 2.0)

        result = build_inspector_state(
            selected_paths=[WITH_GPS, second],
            photo_infos=infos,
            latitude_text="40.1",
            longitude_text="-111.2",
        )

        self.assertEqual(result.apply_hint, "2 photos already have GPS, which will be replaced.")
        self.assertEqual(result.remove_gps_label, "Remove GPS from 2 Photos")


if __name__ == "__main__":
    unittest.main()
