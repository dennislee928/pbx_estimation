from src.research.transport_taxonomy import classify_alternative, classify_solution


def test_esim_api_is_wireless_with_separate_api_capability():
    result = classify_solution({"tags": ["iot", "esim", "api", "cellular"]})
    assert result["primary_bearer"] == "cellular_esim"
    assert result["link_mode"] == "wireless"
    assert result["control_interfaces"] == ["api"]
    assert result["transport_label_zh"] == "蜂巢 / eSIM（無線）"


def test_api_only_platform_does_not_default_to_wired():
    result = classify_solution({"tags": ["cloud", "cpaas", "api"]})
    assert result["primary_bearer"] == "cloud_or_platform"
    assert result["link_mode"] == "unknown"
    assert result["api_capable"] is True


def test_legacy_analog_does_not_gain_api_capability():
    result = classify_solution({"tags": ["tdm", "analog", "fxs", "fxo"]})
    assert result["primary_bearer"] == "analog_tdm"
    assert result["link_mode"] == "wired"
    assert result["network_type"] == "analog"
    assert result["api_capable"] is False


def test_hybrid_ip_pbx_preserves_both_bearers():
    result = classify_solution({"tags": ["ip_pbx", "sip", "fxs"]})
    assert result["primary_bearer"] == "hybrid"
    assert result["link_mode"] == "hybrid"
    assert result["bearers"] == ["analog_tdm", "ethernet"]


def test_wired_non_ip_alternative_is_not_physical_or_api():
    result = classify_alternative({"medium": "serial_wire", "protocols": "RS-485; Modbus RTU"})
    assert result["primary_bearer"] == "serial"
    assert result["link_mode"] == "wired"
    assert result["network_type"] == "non_ip_digital"
    assert result["api_capable"] is False


def test_wireless_alternative_remains_wireless_even_with_api_protocol():
    result = classify_alternative({"medium": "cellular_esim", "protocols": "HTTPS; REST API"})
    assert result["primary_bearer"] == "cellular_esim"
    assert result["link_mode"] == "wireless"
    assert result["api_capable"] is True
