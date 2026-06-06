from __future__ import annotations

import json
import re
from typing import Iterable

TRANSPORT_SCHEMA_VERSION = 2
LABEL_DICTIONARY_VERSION = 2

BEARER_LABELS = {
    "ethernet": ("Ethernet / IP (wired)", "乙太網路 / IP（有線）"),
    "cellular_esim": ("Cellular / eSIM (wireless)", "蜂巢 / eSIM（無線）"),
    "cellular": ("Cellular (wireless)", "蜂巢網路（無線）"),
    "wifi": ("Wi-Fi / IP (wireless)", "Wi-Fi / IP（無線）"),
    "radio": ("Radio / LPWAN (wireless)", "無線電 / LPWAN（無線）"),
    "satellite": ("Satellite (wireless)", "衛星（無線）"),
    "serial": ("Serial line (wired, non-IP)", "序列線路（有線、非 IP）"),
    "fieldbus": ("Fieldbus (wired, non-IP)", "工業匯流排（有線、非 IP）"),
    "powerline": ("Power line (wired)", "電力線（有線）"),
    "electrical_contact": ("Dry contact / relay (physical wired)", "乾接點 / 繼電器（實體有線）"),
    "usb_local_bus": ("Local device bus (wired)", "本地裝置匯流排（有線）"),
    "optical": ("Optical / infrared signal", "光學 / 紅外線訊號"),
    "acoustic": ("Acoustic / audio signal", "聲學 / 音訊訊號"),
    "mechanical": ("Mechanical / fluid actuation", "機械 / 流體致動"),
    "visual_code": ("Visual code / sensor trigger", "視覺碼 / 感測觸發"),
    "manual_process": ("Manual / document process", "人工 / 文件流程"),
    "analog_tdm": ("Analog / TDM (wired)", "類比 / TDM（有線）"),
    "cloud_or_platform": ("Cloud platform (bearer unspecified)", "雲端平台（承載未指定）"),
    "hybrid": ("Hybrid transport", "混合承載"),
    "unknown": ("Bearer unspecified", "承載未指定"),
}

CAPABILITY_LABELS = {
    "api": ("API management", "API 管理"), "rest": ("REST API", "REST API"),
    "graphql": ("GraphQL", "GraphQL"), "webhook": ("Webhook", "Webhook"),
    "sip": ("SIP", "SIP"), "messaging": ("Messaging", "訊息傳遞"),
    "gpio": ("GPIO", "GPIO"), "relay": ("Relay", "繼電器"),
    "serial_protocol": ("Serial protocol", "序列協定"),
    "fieldbus_protocol": ("Fieldbus protocol", "工業匯流排協定"),
    "manual": ("Manual operation", "人工操作"),
}

MEDIUM_RULES = {
    "ethernet_ip": ("ethernet", "ethernet", "wired", "ip"),
    "ethernet_wire": ("ethernet", "ethernet", "wired", "ip"),
    "serial_ethernet": ("ethernet", "ethernet", "wired", "ip"),
    "wifi_direct": ("wifi", "wifi", "wireless", "ip"),
    "cellular": ("cellular", "cellular", "wireless", "ip"),
    "cellular_ip": ("cellular", "cellular", "wireless", "ip"),
    "cellular_lpwans": ("cellular", "cellular", "wireless", "ip"),
    "cellular_esim": ("cellular_esim", "cellular", "wireless", "ip"),
    "private_cellular": ("cellular", "cellular", "wireless", "ip"),
    "cellular_broadcast": ("cellular", "cellular", "wireless", "non_ip_digital"),
    "satellite": ("satellite", "satellite", "wireless", "ip"),
    "satellite_navigation": ("satellite", "satellite", "wireless", "physical_signal"),
    "serial_wire": ("serial", "serial", "wired", "non_ip_digital"),
    "fieldbus": ("fieldbus", "fieldbus", "wired", "non_ip_digital"),
    "building_bus": ("fieldbus", "fieldbus", "wired", "non_ip_digital"),
    "access_control": ("fieldbus", "fieldbus", "wired", "non_ip_digital"),
    "sensor_bus": ("fieldbus", "fieldbus", "wired", "non_ip_digital"),
    "board_bus": ("usb_local_bus", "usb_local_bus", "wired", "non_ip_digital"),
    "usb": ("usb_local_bus", "usb_local_bus", "wired", "non_ip_digital"),
    "av_bus": ("usb_local_bus", "usb_local_bus", "wired", "non_ip_digital"),
    "powerline": ("powerline", "powerline", "wired", "non_ip_digital"),
    "electrical_contact": ("electrical_contact", "electrical_contact", "wired", "physical_signal"),
    "infrared": ("optical", "optical", "contactless", "physical_signal"),
    "optical_signal": ("optical", "optical", "contactless", "physical_signal"),
    "acoustic_signal": ("acoustic", "acoustic", "contactless", "physical_signal"),
    "visual_signal": ("visual_code", "visual_code", "contactless", "physical_signal"),
    "barcode_qr": ("visual_code", "visual_code", "contactless", "physical_signal"),
    "sensor_trigger": ("visual_code", "visual_code", "physical", "physical_signal"),
    "mechanical_actuation": ("mechanical", "mechanical", "physical", "physical_signal"),
    "pneumatic": ("mechanical", "mechanical", "physical", "physical_signal"),
    "hydraulic": ("mechanical", "mechanical", "physical", "physical_signal"),
    "magnetic": ("mechanical", "mechanical", "physical", "physical_signal"),
    "physical_key": ("mechanical", "mechanical", "physical", "physical_signal"),
    "paper_document": ("manual_process", "manual_process", "manual", "manual"),
    "manual_process": ("manual_process", "manual_process", "manual", "manual"),
    "internet_mail": ("cloud_or_platform", "cloud_or_platform", "virtual", "ip"),
    "edge_compute": ("cloud_or_platform", "cloud_or_platform", "virtual", "ip"),
    "edge_ai": ("cloud_or_platform", "cloud_or_platform", "virtual", "ip"),
}

def _tokens(value: object) -> set[str]:
    raw = " ".join(str(item) for item in value) if isinstance(value, (list, tuple, set)) else str(value or "")
    return {token for token in re.split(r"[^a-z0-9_]+", raw.lower().replace("-", "_")) if token}

def _capabilities(tags: Iterable[str] = (), protocols: object = "", text: str = "") -> list[str]:
    tokens = _tokens(tags) | _tokens(protocols) | _tokens(text)
    capabilities = []
    for capability, needles in [
        ("rest", {"rest", "https", "http"}), ("graphql", {"graphql"}),
        ("webhook", {"webhook", "callback"}), ("sip", {"sip", "kpml", "notify", "subscribe"}),
        ("messaging", {"mqtt", "amqp", "sms", "rcs", "message", "messaging"}),
        ("gpio", {"gpio"}), ("relay", {"relay", "contact"}),
        ("serial_protocol", {"serial", "modbus", "rs_232", "rs_485"}),
        ("fieldbus_protocol", {"fieldbus", "can", "profinet", "profibus", "dali", "knx"}),
        ("manual", {"manual", "paper"}),
    ]:
        if tokens & needles:
            capabilities.append(capability)
    if "api" in tokens or any(item in capabilities for item in ("rest", "graphql", "webhook")):
        capabilities.insert(0, "api")
    return list(dict.fromkeys(capabilities))

def _result(primary: str, family: str, mode: str, network: str, capabilities: list[str], *, bearers=None, hybrid=False, confidence="derived", source="tag_rule") -> dict:
    label_en, label_zh = BEARER_LABELS.get(primary, BEARER_LABELS["unknown"])
    return {
        "transport_schema_version": TRANSPORT_SCHEMA_VERSION,
        "label_dictionary_version": LABEL_DICTIONARY_VERSION,
        "primary_bearer": primary, "bearer_family": family, "link_mode": mode,
        "network_type": network, "bearers": list(dict.fromkeys(bearers or [primary])),
        "control_interfaces": capabilities, "api_capable": "api" in capabilities,
        "hybrid": hybrid, "transport_confidence": confidence,
        "transport_classification_source": source,
        "transport_label_en": label_en, "transport_label_zh": label_zh,
        "capability_labels_en": [CAPABILITY_LABELS[item][0] for item in capabilities if item in CAPABILITY_LABELS],
        "capability_labels_zh": [CAPABILITY_LABELS[item][1] for item in capabilities if item in CAPABILITY_LABELS],
    }

def classify_alternative(row: dict) -> dict:
    medium = str(row.get("medium", "")).strip().lower()
    capabilities = _capabilities(protocols=row.get("protocols", ""), text=str(row.get("description", "")))
    if medium in MEDIUM_RULES:
        primary, family, mode, network = MEDIUM_RULES[medium]
        return _result(primary, family, mode, network, capabilities, confidence="explicit", source="medium_rule")
    if medium.startswith("radio_") or medium in {"licensed_radio", "near_field"}:
        return _result("radio", "radio", "wireless", "non_ip_digital", capabilities, confidence="explicit", source="medium_rule")
    return _result("unknown", "unknown", "unknown", "unknown", capabilities, confidence="unknown", source="fallback")

def classify_solution(row: dict) -> dict:
    tags = _tokens(row.get("tags", []))
    capabilities = _capabilities(row.get("tags", []), row.get("protocols", ""), str(row.get("description", "")))
    bearers = []
    if tags & {"esim", "isim"}: bearers.append("cellular_esim")
    elif tags & {"cellular", "nb_iot", "lte_m", "sim"}: bearers.append("cellular")
    if "satellite" in tags: bearers.append("satellite")
    if tags & {"wifi", "wlan"}: bearers.append("wifi")
    if tags & {"tdm", "analog", "pots", "fxs", "fxo", "digital"}: bearers.append("analog_tdm")
    if tags & {"ip_pbx", "sip", "voip", "webrtc"}: bearers.append("ethernet")
    bearers = list(dict.fromkeys(bearers))
    if len(bearers) > 1:
        return _result("hybrid", "hybrid", "hybrid", "mixed", capabilities, bearers=bearers, hybrid=True)
    if bearers:
        primary = bearers[0]
        if primary in {"cellular", "cellular_esim", "satellite", "wifi"}:
            family = "cellular" if primary in {"cellular", "cellular_esim"} else primary
            return _result(primary, family, "wireless", "ip", capabilities)
        if primary == "analog_tdm":
            return _result(primary, "analog_tdm", "wired", "analog", capabilities)
        return _result(primary, "ethernet", "wired", "ip", capabilities)
    if tags & {"cloud", "ucaas", "cpaas", "hosted", "telco", "contact_center", "call_center", "voice", "api"}:
        return _result("cloud_or_platform", "cloud_or_platform", "unknown", "ip", capabilities)
    return _result("unknown", "unknown", "unknown", "unknown", capabilities, confidence="unknown", source="fallback")

def serialize_for_csv(value: object) -> object:
    if isinstance(value, (list, dict)): return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, bool): return "true" if value else "false"
    return value
