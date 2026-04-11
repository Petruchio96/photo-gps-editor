import unittest
from pathlib import Path

from core.models import GpsCoordinates, PhotoInfo
from services.gps_workflow_service import apply_gps_to_paths, prepare_apply_gps
from services.models import SourceResolution


class StubWriter:
    def __init__(self, failing_paths: set[Path] | None = None) -> None:
        self.calls: list[tuple[Path, float, float]] = []
        self.failing_paths = failing_paths or set()

    def write_gps(self, path: Path, latitude: float, longitude: float) -> None:
        self.calls.append((path, latitude, longitude))
        if path in self.failing_paths:
            raise RuntimeError("boom")


class GpsWorkflowServiceTests(unittest.TestCase):
    def test_prepare_apply_gps_rejects_empty_destination_selection(self) -> None:
        preparation = prepare_apply_gps(
            selected_paths=[],
            using_photo_source=False,
            source_photo_path=None,
            source_resolution=SourceResolution(
                coordinates=GpsCoordinates(40.5, -111.8)
            ),
            photo_info_by_path={},
        )

        self.assertEqual(
            preparation.error_message,
            "Select one or more destination photos before applying GPS.",
        )

    def test_prepare_apply_gps_collects_overwrite_entries(self) -> None:
        source_path = Path("/tmp/source.jpg")
        target_path = Path("/tmp/target.jpg")
        preparation = prepare_apply_gps(
            selected_paths=[source_path, target_path],
            using_photo_source=True,
            source_photo_path=source_path,
            source_resolution=SourceResolution(
                coordinates=GpsCoordinates(40.5, -111.8)
            ),
            photo_info_by_path={
                target_path: PhotoInfo(
                    path=target_path,
                    file_type="JPG",
                    current_latitude=41.0,
                    current_longitude=-112.0,
                )
            },
        )

        self.assertEqual(preparation.target_paths, [target_path])
        self.assertEqual(
            [entry.display_text() for entry in preparation.overwrite_entries],
            ["target.jpg — 41.000000, -112.000000"],
        )

    def test_apply_gps_to_paths_collects_successes_and_failures(self) -> None:
        first = Path("/tmp/first.jpg")
        second = Path("/tmp/second.jpg")
        writer = StubWriter(failing_paths={second})

        result = apply_gps_to_paths(
            [first, second],
            latitude=40.5,
            longitude=-111.8,
            writer=writer,
        )

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failed_paths, ["second.jpg: boom"])
        self.assertEqual(
            writer.calls,
            [
                (first, 40.5, -111.8),
                (second, 40.5, -111.8),
            ],
        )


if __name__ == "__main__":
    unittest.main()
