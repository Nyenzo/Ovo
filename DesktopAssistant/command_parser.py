import re


def parse_weather_command(command):
    """Return the requested weather operation and city, if both are present."""
    normalized = " ".join(command.lower().split())
    patterns = (
        ("forecast", r"(?:weather forecast|forecast)(?: for| in) (?P<city>.+)"),
        ("current", r"(?:current weather|weather)(?: for| in) (?P<city>.+)"),
    )

    for operation, pattern in patterns:
        match = re.fullmatch(pattern, normalized)
        if match:
            city = match.group("city").strip()
            if city:
                return operation, city

    return None, None
