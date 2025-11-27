"""Tests for logging utilities."""

from nauyaca.utils.logging import hash_ip_processor


def test_hash_ip_processor_hashes_ip():
    """Test that hash_ip_processor hashes client_ip."""
    event_dict = {"client_ip": "192.168.1.100", "message": "test"}

    result = hash_ip_processor(None, "info", event_dict)

    # Original IP should be removed
    assert "client_ip" not in result
    # Hash should be added
    assert "client_ip_hash" in result
    # Hash should be 12 chars (truncated SHA256)
    assert len(result["client_ip_hash"]) == 12
    # Message should be preserved
    assert result["message"] == "test"


def test_hash_ip_processor_same_ip_same_hash():
    """Test that same IP always produces same hash."""
    event1 = {"client_ip": "192.168.1.100"}
    event2 = {"client_ip": "192.168.1.100"}

    result1 = hash_ip_processor(None, "info", event1)
    result2 = hash_ip_processor(None, "info", event2)

    assert result1["client_ip_hash"] == result2["client_ip_hash"]


def test_hash_ip_processor_different_ip_different_hash():
    """Test that different IPs produce different hashes."""
    event1 = {"client_ip": "192.168.1.100"}
    event2 = {"client_ip": "192.168.1.101"}

    result1 = hash_ip_processor(None, "info", event1)
    result2 = hash_ip_processor(None, "info", event2)

    assert result1["client_ip_hash"] != result2["client_ip_hash"]


def test_hash_ip_processor_skips_unknown():
    """Test that 'unknown' IP is skipped."""
    event_dict = {"client_ip": "unknown", "message": "test"}

    result = hash_ip_processor(None, "info", event_dict)

    # IP should remain as-is (not hashed)
    assert "client_ip" in result
    assert result["client_ip"] == "unknown"
    assert "client_ip_hash" not in result


def test_hash_ip_processor_skips_missing():
    """Test that missing client_ip is handled."""
    event_dict = {"message": "test"}

    result = hash_ip_processor(None, "info", event_dict)

    # Nothing should change
    assert "client_ip" not in result
    assert "client_ip_hash" not in result
    assert result["message"] == "test"


def test_hash_ip_processor_skips_empty():
    """Test that empty client_ip is skipped."""
    event_dict = {"client_ip": "", "message": "test"}

    result = hash_ip_processor(None, "info", event_dict)

    # Empty IP should remain as-is
    assert "client_ip" in result
    assert result["client_ip"] == ""
    assert "client_ip_hash" not in result
