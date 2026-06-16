from gw2radar.ingest.gw2_api_client import GW2ApiClient


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return b'{"ok": true}'


class RecordingOpener:
    def __init__(self) -> None:
        self.requests = []

    def __call__(self, request, timeout: float):
        self.requests.append((request, timeout))
        return FakeResponse()


def test_official_client_defaults_to_guild_wars_2_api_base_url() -> None:
    client = GW2ApiClient(opener=RecordingOpener())
    assert client.base_url == "https://api.guildwars2.com"


def test_fetch_tokeninfo_uses_authorization_header_only() -> None:
    opener = RecordingOpener()
    client = GW2ApiClient(base_url="https://example.test", opener=opener)

    payload = client.fetch_tokeninfo("12345678-abcdef-secret-key", request_id="req-tokeninfo")

    request, _timeout = opener.requests[0]
    assert payload == {"ok": True}
    assert request.full_url == "https://example.test/v2/tokeninfo"
    assert "12345678-abcdef-secret-key" not in request.full_url
    assert request.headers["Authorization"] == "Bearer 12345678-abcdef-secret-key"
