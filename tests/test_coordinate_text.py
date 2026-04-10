import unittest

from gui.services.coordinate_text import (
    parse_coordinate_text,
    parse_latitude_text,
    parse_longitude_text,
    parse_manual_coordinates,
)


class CoordinateTextParsingTests(unittest.TestCase):
    def test_parse_latitude_supports_decimal_and_dms(self) -> None:
        self.assertEqual(parse_latitude_text("40.5"), 40.5)
        self.assertAlmostEqual(parse_latitude_text("40°42'51\"N"), 40.71416666666667)

    def test_parse_longitude_supports_prefix_direction(self) -> None:
        self.assertAlmostEqual(parse_longitude_text("W 111°48'48\""), -111.81333333333333)

    def test_parse_coordinate_text_supports_comma_separated_pair(self) -> None:
        self.assertEqual(
            parse_coordinate_text("40.486325, -111.813415"),
            ("40.486325", "-111.813415"),
        )

    def test_parse_coordinate_text_supports_space_before_directions(self) -> None:
        self.assertEqual(
            parse_coordinate_text('40°42\'51"N 74°00\'21"W'),
            ('40°42\'51"N', '74°00\'21"W'),
        )

    def test_parse_coordinate_text_supports_plain_numeric_pairs(self) -> None:
        self.assertEqual(
            parse_coordinate_text("40.486325 -111.813415"),
            ("40.486325", "-111.813415"),
        )

    def test_parse_coordinate_text_rejects_invalid_pair(self) -> None:
        self.assertIsNone(parse_coordinate_text("40, west"))
        self.assertIsNone(parse_coordinate_text(""))

    def test_parse_manual_coordinates_requires_both_fields(self) -> None:
        self.assertIsNone(parse_manual_coordinates("", "-111.8"))
        self.assertIsNone(parse_manual_coordinates("40.5", ""))

    def test_parse_manual_coordinates_returns_decimal_pair(self) -> None:
        self.assertEqual(
            parse_manual_coordinates("40.486325", "-111.813415"),
            (40.486325, -111.813415),
        )

    def test_conflicting_directions_raise_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            parse_latitude_text("N 40 S")

    def test_sign_and_direction_together_raise_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "sign and compass direction"):
            parse_longitude_text("-111W")

    def test_out_of_range_minutes_and_seconds_raise_value_error(self) -> None:
        with self.assertRaises(ValueError):
            parse_latitude_text("40°60'0\"N")

        with self.assertRaises(ValueError):
            parse_longitude_text("111°30'60\"W")


if __name__ == "__main__":
    unittest.main()
