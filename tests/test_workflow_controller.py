import unittest
from pathlib import Path

from core.models import GpsCoordinates, PhotoInfo
from services.models import ApplyPreparation, WorkflowSession
from services.workflow_controller import (
    clear_source_workflow,
    execute_apply_workflow,
    load_source_workflow,
    prepare_apply_workflow,
    refresh_destination_workflow,
)


class StubLoader:
    def __init__(self, photo_infos: dict[Path, PhotoInfo]) -> None:
        self.photo_infos = photo_infos
        self.calls: list[Path] = []

    def load_photo_info(self, path: Path) -> PhotoInfo:
        self.calls.append(path)
        return self.photo_infos[path]


class StubWriter:
    def __init__(self, failing_paths: set[Path] | None = None) -> None:
        self.calls: list[tuple[Path, float, float]] = []
        self.failing_paths = failing_paths or set()

    def write_gps(self, path: Path, latitude: float, longitude: float) -> None:
        self.calls.append((path, latitude, longitude))
        if path in self.failing_paths:
            raise RuntimeError("boom")


class WorkflowControllerTests(unittest.TestCase):
    def test_refresh_destination_workflow_preserves_source_state(self) -> None:
        source = Path("/tmp/source.jpg")
        destination = Path("/tmp/destination.jpg")
        source_info = PhotoInfo(
            path=source,
            file_type="JPG",
            current_latitude=40.5,
            current_longitude=-111.8,
        )
        loader = StubLoader(
            {
                destination: PhotoInfo(path=destination, file_type="JPG"),
            }
        )
        session = WorkflowSession(
            selected_paths=[destination],
            source_photo_info=source_info,
            source_photo_path=source,
        )

        refreshed = refresh_destination_workflow(session, loader)

        self.assertEqual(refreshed.selected_paths, [destination])
        self.assertEqual(refreshed.thumbnail_items, [])
        self.assertEqual(refreshed.source_photo_path, source)
        self.assertEqual(refreshed.source_photo_info, source_info)

    def test_load_source_workflow_sets_session_and_returns_success_message(self) -> None:
        source = Path("/tmp/source.jpg")
        source_info = PhotoInfo(
            path=source,
            file_type="JPG",
            current_latitude=40.5,
            current_longitude=-111.8,
        )
        session = WorkflowSession()
        loader = StubLoader({source: source_info})

        result = load_source_workflow(session, source, loader)

        self.assertEqual(result.session.source_photo_path, source)
        self.assertEqual(result.session.source_photo_info, source_info)
        self.assertEqual(result.message.text, "Source photo loaded and ready to apply.")
        self.assertEqual(result.message.tone, "success")

    def test_clear_source_workflow_clears_session_and_returns_message(self) -> None:
        session = WorkflowSession(
            source_photo_path=Path("/tmp/source.jpg"),
            source_photo_info=PhotoInfo(path=Path("/tmp/source.jpg"), file_type="JPG"),
        )

        message = clear_source_workflow(session)

        self.assertIsNone(session.source_photo_path)
        self.assertIsNone(session.source_photo_info)
        self.assertEqual(message.text, "Source photo cleared.")
        self.assertEqual(message.tone, "info")

    def test_prepare_apply_workflow_uses_session_state(self) -> None:
        source = Path("/tmp/source.jpg")
        destination = Path("/tmp/destination.jpg")
        session = WorkflowSession(
            source_photo_path=source,
            source_photo_info=PhotoInfo(
                path=source,
                file_type="JPG",
                current_latitude=40.5,
                current_longitude=-111.8,
            ),
            loaded_photo_infos={
                destination: PhotoInfo(
                    path=destination,
                    file_type="JPG",
                    current_latitude=41.0,
                    current_longitude=-112.0,
                )
            },
        )

        preparation = prepare_apply_workflow(
            session=session,
            selected_paths=[source, destination],
            using_photo_source=True,
            latitude_text="",
            longitude_text="",
        )

        self.assertEqual(preparation.target_paths, [destination])
        self.assertEqual(
            [entry.display_text() for entry in preparation.overwrite_entries],
            ["destination.jpg — 41.000000, -112.000000"],
        )
        self.assertEqual(preparation.coordinates, GpsCoordinates(40.5, -111.8))

    def test_execute_apply_workflow_refreshes_session_after_write(self) -> None:
        destination = Path("/tmp/destination.jpg")
        session = WorkflowSession(
            selected_paths=[destination],
            source_photo_path=Path("/tmp/source.jpg"),
        )
        loader = StubLoader(
            {
                destination: PhotoInfo(
                    path=destination,
                    file_type="JPG",
                    current_latitude=40.5,
                    current_longitude=-111.8,
                )
            }
        )
        writer = StubWriter()

        result = execute_apply_workflow(
            session=session,
            preparation=ApplyPreparation(
                target_paths=[destination],
                coordinates=GpsCoordinates(40.5, -111.8),
            ),
            writer=writer,
            loader=loader,
        )

        self.assertEqual(writer.calls, [(destination, 40.5, -111.8)])
        self.assertEqual(result.execution_result.success_count, 1)
        self.assertEqual(result.session.selected_paths, [destination])
        self.assertEqual(result.session.source_photo_path, Path("/tmp/source.jpg"))
        self.assertIn(destination, result.session.loaded_photo_infos)


if __name__ == "__main__":
    unittest.main()
