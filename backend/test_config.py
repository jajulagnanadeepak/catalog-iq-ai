"""Configuration smoke check.

Previously this module printed the MongoDB URL and JWT secret at import time,
so any pytest run that collected it exposed them in the output. It now only
asserts that the settings load and are populated, and never prints values.
"""

from config import settings


def test_settings_load_and_are_populated(capsys):
    assert settings.mongodb_url
    assert settings.database_name
    assert settings.jwt_secret

    # Nothing about the configuration may reach stdout/stderr.
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
