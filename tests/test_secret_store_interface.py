from gw2radar.security.in_memory_secret_store import InMemorySecretStore


def test_in_memory_secret_store_round_trips_in_test_mode() -> None:
    store = InMemorySecretStore()
    record = store.put_api_key("user-1", "12345678-abcdef-secret-key")

    assert record.user_id == "user-1"
    assert record.encrypted is False
    assert store.get_api_key("user-1") == "12345678-abcdef-secret-key"
    assert store.get_status("user-1").has_api_key is True
    assert store.delete_api_key("user-1") is True
    assert store.get_api_key("user-1") is None
