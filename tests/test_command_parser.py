import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "DesktopAssistant"))

from command_parser import parse_weather_command


class ParseWeatherCommandTests(unittest.TestCase):
    def test_parses_documented_forecast_command(self):
        self.assertEqual(
            parse_weather_command("weather forecast in London"),
            ("forecast", "london"),
        )

    def test_forecast_is_not_mistaken_for_current_weather_city(self):
        operation, city = parse_weather_command("weather forecast in New York")

        self.assertEqual(operation, "forecast")
        self.assertEqual(city, "new york")

    def test_parses_current_weather_command(self):
        self.assertEqual(
            parse_weather_command("current weather in São Paulo"),
            ("current", "são paulo"),
        )

    def test_requires_a_city(self):
        self.assertEqual(parse_weather_command("weather forecast"), (None, None))


if __name__ == "__main__":
    unittest.main()
