import unittest

from core.coordinates import (
    validate_coordinates,
    validate_latitude,
    validate_longitude,
)


class CoordinateValidationTests(unittest.TestCase):
    def test_validate_latitude_accepts_boundaries(self) -> None:
        self.assertEqual(validate_latitude("-90"), -90.0)
        self.assertEqual(validate_latitude("90"), 90.0)

    def test_validate_latitude_rejects_out_of_range_values(self) -> None:
        with self.assertRaises(ValueError):
            validate_latitude("-90.1")

        with self.assertRaises(ValueError):
            validate_latitude("90.1")

    def test_validate_longitude_accepts_boundaries(self) -> None:
        self.assertEqual(validate_longitude("-180"), -180.0)
        self.assertEqual(validate_longitude("180"), 180.0)

    def test_validate_longitude_rejects_out_of_range_values(self) -> None:
        with self.assertRaises(ValueError):
            validate_longitude("-180.1")

        with self.assertRaises(ValueError):
            validate_longitude("180.1")

    def test_validate_coordinates_returns_pair(self) -> None:
        self.assertEqual(validate_coordinates("40.5", "-111.8"), (40.5, -111.8))

    def test_validate_coordinates_raises_for_non_numeric_values(self) -> None:
        with self.assertRaises(ValueError):
            validate_coordinates("north", "west")


if __name__ == "__main__":
    unittest.main()
