from nico.integrations.google.credentials import get_credentials


def test_get_credentials_returns_none_without_api_libs() -> None:
    result = get_credentials(
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        credentials_file=None,
        token_file=None,
    )
    assert result is None
