import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional

# --- PSTN-alternative catalog ---
# Each entry: alternative to using a physical phone line to trigger/send a command to an edge device

PSTN_ALTERNATIVES_CABLE = [
    {
        "name": "SIP INFO / REFER",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "Send commands to edge devices via SIP signaling messages (INFO, REFER, NOTIFY) over an IP network using existing SIP infrastructure.",
        "protocols": ["SIP", "SDP", "RTP"],
        "latency": "<100ms",
        "bandwidth": "<1 Kbps per message",
        "reliability": "High on QoS-managed networks",
        "security": "TLS 1.2/1.3, SRTP, mutual authentication",
        "complexity": "Medium",
        "cost": "Low (uses existing SIP trunk)",
        "use_case": "Trigger paging, door open, alarm via PBX extension dialing",
        "pros": [
            "Leverages existing VoIP/PBX infrastructure already deployed",
            "Standards-based (RFC 3261, RFC 2976)",
            "Low latency on managed networks",
            "Works through SBCs and firewalls with proper SIP ALG",
        ],
        "cons": [
            "Requires SIP stack on edge device",
            "Network QoS essential for reliability",
            "SIP ALG/firewall traversal can be brittle",
            "Limited data payload per message",
        ],
        "standards": ["RFC 3261", "RFC 2976", "RFC 3515"],
    },
    {
        "name": "REST API (HTTP/HTTPS)",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "Edge device exposes HTTP endpoint; PBX/controller sends POST/GET requests to trigger actions or retrieve status.",
        "protocols": ["HTTP/1.1", "HTTP/2", "HTTPS", "JSON", "XML"],
        "latency": "<50ms on LAN, 50-200ms on WAN",
        "bandwidth": "<0.5 KB per request",
        "reliability": "Very High",
        "security": "TLS 1.3, API keys, OAuth 2.0, mTLS, IP allowlisting",
        "complexity": "Low",
        "cost": "Very Low (standard TCP/IP networking)",
        "use_case": "Trigger relay, GPIO, read sensor, set parameter on edge device from any HTTP-capable system",
        "pros": [
            "Ubiquitous protocol, any modern device supports HTTP",
            "Simple to implement and debug (curl, Postman)",
            "Secure with HTTPS + API keys",
            "Language-agnostic: any PBX or automation platform can call REST endpoints",
        ],
        "cons": [
            "Edge device must be IP-reachable",
            "HTTP overhead for very constrained devices",
            "Stateless; requires polling or webhook pattern for events",
            "Not real-time for <10ms requirements",
        ],
        "standards": ["RFC 7230", "RFC 8446"],
    },
    {
        "name": "WebSocket (wss://)",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "Persistent bidirectional channel between PBX/controller and edge device over WebSocket protocol, enabling real-time command push.",
        "protocols": ["WebSocket", "WSS", "JSON"],
        "latency": "<10ms on LAN",
        "bandwidth": "~100 bytes per message",
        "reliability": "High (persistent connection with auto-reconnect)",
        "security": "WSS (TLS 1.3), origin validation, token auth",
        "complexity": "Medium",
        "cost": "Low",
        "use_case": "Real-time push of commands to edge devices, live status monitoring, streaming telemetry",
        "pros": [
            "Full-duplex persistent connection",
            "Low latency, suitable for real-time control",
            "Supports binary and text payloads",
            "Widely supported in modern edge computing platforms",
        ],
        "cons": [
            "Requires persistent TCP connection",
            "Edge device must support WebSocket stack",
            "Proxy/firewall may block WebSocket upgrade",
            "Connection state management complexity at scale",
        ],
        "standards": ["RFC 6455", "RFC 7692"],
    },
    {
        "name": "MQTT (MQTT-SN)",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "Lightweight publish/subscribe messaging protocol designed for constrained devices and low-bandwidth networks. MQTT-SN extends to non-TCP networks.",
        "protocols": ["MQTT 3.1.1", "MQTT 5.0", "MQTT-SN"],
        "latency": "<50ms on LAN, 100-500ms on WAN",
        "bandwidth": "Minimal (2-byte header minimum)",
        "reliability": "High (3 QoS levels, persistent session, last will)",
        "security": "TLS 1.2/1.3, username/password, X.509 certs, OAuth",
        "complexity": "Low",
        "cost": "Very Low",
        "use_case": "IoT edge device command/control, sensor telemetry, distributed relay triggering across many devices",
        "pros": [
            "Extremely lightweight; designed for IoT/edge",
            "Pub/sub decouples sender and receiver",
            "Three QoS levels (at most once, at least once, exactly once)",
            "Last Will & Testament for device failure detection",
            "Very mature ecosystem (AWS IoT, Azure IoT Hub, EMQX, Mosquitto)",
        ],
        "cons": [
            "Requires MQTT broker (single point of failure without clustering)",
            "Not real-time enough for sub-10ms control loops",
            "TCP-based; MQTT-SN adds non-IP support but less mature",
            "Broker discovery and topic governance needed at scale",
        ],
        "standards": ["OASIS MQTT 3.1.1", "OASIS MQTT 5.0", "ISO/IEC 20922"],
    },
    {
        "name": "WebRTC Data Channel",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "Peer-to-peer data channel between browser/app and edge device, using SCTP over DTLS. Enables low-latency command and control with NAT traversal built-in.",
        "protocols": ["SCTP", "DTLS", "ICE", "STUN", "TURN"],
        "latency": "<10ms on LAN, 20-100ms on WAN",
        "bandwidth": "~1-10 Kbps per channel",
        "reliability": "High (configurable: reliable vs unreliable mode)",
        "security": "DTLS 1.3, mandatory encryption, ICE consent freshness",
        "complexity": "High",
        "cost": "Low (no infrastructure needed for P2P)",
        "use_case": "Browser-based control panels for edge devices, peer-to-peer device management without cloud relay",
        "pros": [
            "Mandatory encryption (no option for plaintext)",
            "Built-in NAT traversal via ICE/STUN/TURN",
            "Low latency, suitable for real-time control",
            "Can operate peer-to-peer without intermediate server",
        ],
        "cons": [
            "High complexity to implement",
            "TURN server needed for symmetric NAT scenarios",
            "Not all embedded platforms have WebRTC stack",
            "Overkill for simple trigger/command use cases",
        ],
        "standards": ["W3C WebRTC", "RFC 8831", "RFC 8832"],
    },
    {
        "name": "gRPC (HTTP/2)",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "High-performance RPC framework using Protocol Buffers over HTTP/2. Supports bidirectional streaming, ideal for structured command/control.",
        "protocols": ["HTTP/2", "Protocol Buffers", "gRPC", "gRPC-Web"],
        "latency": "<5ms on LAN",
        "bandwidth": "~100 bytes per message (binary encoding)",
        "reliability": "Very High",
        "security": "TLS 1.3, mTLS, OAuth, JWT",
        "complexity": "Medium-High",
        "cost": "Low",
        "use_case": "Structured command/control between microservices and edge devices, streaming telemetry, bidirectional RPC",
        "pros": [
            "Binary encoding (Protocol Buffers) is efficient",
            "Strong typing with .proto schema",
            "Bidirectional streaming built-in",
            "Excellent performance and tooling (protoc, code generation)",
        ],
        "cons": [
            "HTTP/2 requirement may not suit very constrained MCUs",
            "gRPC-Web has limitations vs native gRPC",
            "Protocol Buffers schema management overhead",
            "Steeper learning curve than REST",
        ],
        "standards": ["gRPC 1.x", "HTTP/2 (RFC 7540)", "Protocol Buffers"],
    },
    {
        "name": "CoAP (Constrained Application Protocol)",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "UDP-based REST-like protocol designed for IoT/constrained devices. Supports multicast, discovery, and asynchronous subscriptions.",
        "protocols": ["CoAP", "DTLS", "UDP"],
        "latency": "<10ms on LAN",
        "bandwidth": "Minimal (4-byte header)",
        "reliability": "Medium (CON/NON messages, retransmission)",
        "security": "DTLS 1.2/1.3, OSCORE, RawPublicKey",
        "complexity": "Low-Medium",
        "cost": "Very Low",
        "use_case": "Constrained edge devices (MCU, 8-bit) that need simple REST-like command/control over UDP",
        "pros": [
            "UDP-based, no TCP overhead",
            "Very small header (4 bytes)",
            "Built-in resource discovery",
            "Observations (pub/sub over UDP)",
        ],
        "cons": [
            "UDP may be blocked in some networks",
            "Less mature ecosystem than MQTT",
            "Reliability is best-effort without CON mode",
            "Not suitable for large payloads",
        ],
        "standards": ["RFC 7252", "RFC 7641", "RFC 8613"],
    },
    {
        "name": "GraphQL API / Subscriptions",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "Expose device command and state as a typed GraphQL schema, with subscriptions for event streams.",
        "protocols": ["GraphQL", "HTTP/2", "WebSocket", "JSON"],
        "latency": "<50ms on LAN",
        "bandwidth": "Request dependent",
        "reliability": "High",
        "security": "TLS 1.3, OAuth 2.0, mTLS, field-level authorization",
        "complexity": "Medium-High",
        "cost": "Low-Medium",
        "use_case": "Unified API facade for mixed PBX, CRM, alarm, and edge-device control surfaces",
        "pros": [
            "Strong schema contracts for frontend and backend teams",
            "Subscriptions support live state updates",
            "Good aggregation layer when multiple device APIs differ",
        ],
        "cons": [
            "Adds an API gateway layer",
            "Resolver authorization must be designed carefully",
            "Less suitable for tiny microcontrollers than REST or CoAP",
        ],
        "standards": ["GraphQL Specification", "RFC 8446"],
    },
    {
        "name": "Webhook Callback",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "PBX, UCaaS, or monitoring system posts signed event callbacks to an integration service that commands edge devices.",
        "protocols": ["HTTPS", "JSON", "HMAC", "JWT"],
        "latency": "50-500ms typical",
        "bandwidth": "<2 KB per event",
        "reliability": "High with retry queues",
        "security": "TLS 1.3, HMAC signatures, replay protection, IP allowlisting",
        "complexity": "Low-Medium",
        "cost": "Very Low",
        "use_case": "Cloud PBX call event triggers, alarm notification fanout, CRM-to-device workflows",
        "pros": [
            "Simple cloud integration pattern",
            "No polling when source system supports events",
            "Works well with serverless queues and audit logs",
        ],
        "cons": [
            "Receiver must be internet reachable",
            "Retries can duplicate actions unless idempotency is implemented",
            "Vendor webhook schemas vary",
        ],
        "standards": ["HTTP", "JSON Web Signature patterns", "RFC 8446"],
    },
    {
        "name": "AMQP / RabbitMQ",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "Use a durable message broker for queued commands, acknowledgements, and dead-letter handling.",
        "protocols": ["AMQP 0-9-1", "AMQP 1.0", "TLS"],
        "latency": "<10ms on LAN",
        "bandwidth": "Small binary or JSON messages",
        "reliability": "Very High with durable queues",
        "security": "TLS, SASL, vhost permissions, mTLS",
        "complexity": "Medium",
        "cost": "Low-Medium",
        "use_case": "Reliable command dispatch where every action must be auditable and retried",
        "pros": [
            "Durable queues and acknowledgements",
            "Dead-letter queues expose failed device commands",
            "Mature operations model",
        ],
        "cons": [
            "Broker infrastructure required",
            "Not ideal for battery-powered devices",
            "Queue design affects ordering and fanout",
        ],
        "standards": ["AMQP 0-9-1", "AMQP 1.0"],
    },
    {
        "name": "NATS / JetStream",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "Lightweight subject-based messaging with optional persistence for low-latency command and telemetry flows.",
        "protocols": ["NATS", "JetStream", "TLS"],
        "latency": "<5ms on LAN",
        "bandwidth": "Small text/binary messages",
        "reliability": "High with JetStream persistence",
        "security": "TLS, nkeys, JWT account authorization",
        "complexity": "Medium",
        "cost": "Low",
        "use_case": "Edge fleets, microservices, low-latency pub/sub command buses",
        "pros": [
            "Very low latency and simple clients",
            "Request/reply and pub/sub in one protocol",
            "Persistence available when needed",
        ],
        "cons": [
            "Smaller enterprise PBX ecosystem than MQTT or AMQP",
            "Requires subject naming discipline",
            "Native clients may be unavailable on constrained legacy devices",
        ],
        "standards": ["NATS Protocol"],
    },
    {
        "name": "OPC UA",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "Industrial interoperability protocol for secure device command, telemetry, and semantic information models.",
        "protocols": ["OPC UA", "UA Binary", "HTTPS", "PubSub"],
        "latency": "<10ms to 100ms",
        "bandwidth": "Variable",
        "reliability": "Very High",
        "security": "X.509 certificates, signing, encryption, user tokens",
        "complexity": "High",
        "cost": "Medium-High",
        "use_case": "Factory, building automation, and industrial facilities integrating telephony events with PLC/SCADA assets",
        "pros": [
            "Vendor-neutral industrial data model",
            "Strong built-in security model",
            "Widely supported by automation vendors",
        ],
        "cons": [
            "Overkill for simple office relay control",
            "Certificate lifecycle adds operational work",
            "Industrial expertise needed",
        ],
        "standards": ["IEC 62541"],
    },
    {
        "name": "Modbus TCP",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "Ethernet version of Modbus register reads/writes for simple PLC, relay, and I/O module command.",
        "protocols": ["Modbus TCP", "TCP"],
        "latency": "<10ms on LAN",
        "bandwidth": "Minimal register frames",
        "reliability": "High on isolated LANs",
        "security": "None natively; isolate with VPN, firewall, or TLS gateway",
        "complexity": "Low",
        "cost": "Low",
        "use_case": "PBX-triggered relay outputs in industrial or building-control panels",
        "pros": [
            "Extremely common in PLC and I/O devices",
            "Simple register model",
            "Low-cost hardware modules are widely available",
        ],
        "cons": [
            "No native authentication or encryption",
            "Flat register maps can be error-prone",
            "Needs network isolation",
        ],
        "standards": ["Modbus Application Protocol"],
    },
]

PSTN_ALTERNATIVES_WIRELESS = [
    {
        "name": "LoRaWAN",
        "category": "non_web",
        "medium": "radio_ism",
        "description": "Long-range, low-power wireless protocol for IoT in unlicensed ISM bands. Edge devices receive downlink commands from a LoRaWAN network server.",
        "protocols": ["LoRaWAN 1.0.4", "LoRaWAN 1.1", "RP002-1.0.3"],
        "latency": "1-10 seconds (class A), <100ms (class B/C)",
        "bandwidth": "0.3-50 Kbps",
        "range": "2-15 km (urban), 10-30 km (rural)",
        "reliability": "Medium (spread-spectrum, duty-cycle limits)",
        "security": "AES-128 CTR + CMAC (end-to-end), FRM payload encryption, JoinEUI/DevEUI",
        "complexity": "Medium",
        "cost": "Low (module $5-15, network server open-source or cloud)",
        "use_case": "Remote trigger of edge devices where no IP connectivity exists (agriculture, rural infrastructure, pipelines)",
        "pros": [
            "Exceptional range (kilometers) with very low power",
            "No cellular subscription needed (ISM band)",
            "Excellent building penetration",
            "Bi-directional downlink for command/control",
            "Open standard, multi-vendor ecosystem (TTN, Helium, AWS IoT)",
        ],
        "cons": [
            "Very low data rate (not for large payloads)",
            "Duty-cycle restrictions in EU (868 MHz)",
            "Class A devices cannot receive downlink until they send uplink",
            "Latency too high for real-time control",
        ],
        "standards": ["LoRaWAN L2 1.0.4", "ETSI EN 300 220", "FCC Part 15"],
    },
    {
        "name": "SMS / GSM AT Commands",
        "category": "non_web",
        "medium": "cellular",
        "description": "Send commands to edge devices via SMS messages or direct GSM AT commands over cellular network. Widely available even in remote areas.",
        "protocols": ["SMS (GSM 03.38)", "AT (GSM 07.07)", "USSD"],
        "latency": "1-30 seconds (SMS), <1s (AT command)",
        "bandwidth": "160 bytes per SMS",
        "range": "Anywhere with cellular coverage",
        "reliability": "High (store-and-forward SMS), Medium (AT on circuit-switched)",
        "security": "SMS is encrypted over-the-air (A5/3) but not end-to-end; SS7 vulnerabilities known",
        "complexity": "Low",
        "cost": "Low-Medium ($0.01-0.10 per SMS, GSM module $10-30)",
        "use_case": "Remote sites with only cellular coverage, backup trigger path, offline command delivery",
        "pros": [
            "Works anywhere there is cellular coverage",
            "GSM modules are cheap and widely available",
            "Simple AT command interface",
            "SMS is store-and-forward (device can receive when offline)",
            "Bidirectional (2-way SMS)",
        ],
        "cons": [
            "SMS latency varies (1-30s typical, can be hours)",
            "SMS is not end-to-end encrypted by default",
            "SS7 vulnerabilities allow SMS interception",
            "Per-message cost at scale",
            "2G/3G sunsetting reduces GSM availability in some regions",
        ],
        "standards": ["GSM 03.38", "GSM 07.07", "3GPP TS 23.040"],
    },
    {
        "name": "Z-Wave / Zigbee",
        "category": "non_web",
        "medium": "radio_subghz_24ghz",
        "description": "Short-range mesh RF protocols for home/building automation. Edge devices (relays, sensors, locks) are controlled via controllers that can be triggered from PBX/integration layer.",
        "protocols": ["Z-Wave (ITU-T G.9959)", "Zigbee 3.0", "Zigbee PRO"],
        "latency": "<100ms",
        "bandwidth": "100 Kbps (Z-Wave), 250 Kbps (Zigbee)",
        "range": "30-50m per node (mesh extends significantly)",
        "reliability": "High (mesh topology, ACk, retry)",
        "security": "Z-Wave S2 (mandatory), Zigbee APS encryption (AES-128-CCM*)",
        "complexity": "Low-Medium",
        "cost": "Low (Z-Wave/Zigbee modules $3-10, controllers $30-100)",
        "use_case": "In-building edge device control (lighting, door lock, relay) via office PBX/automation integration",
        "pros": [
            "Mature ecosystem with thousands of interoperable devices",
            "Mesh topology extends range across buildings",
            "Low power (battery for sensors)",
            "Z-Wave S2 has strong security (mandatory since 2017)",
            "Direct integration with home/office automation hubs",
        ],
        "cons": [
            "Short range per node without mesh",
            "Z-Wave and Zigbee are different ecosystems (no interoperability)",
            "Requires hub/controller for PBX integration",
            "Limited to building-scale; not for outdoor/long-range",
            "Z-Wave chips supply constraints historically",
        ],
        "standards": ["Z-Wave (ITU-T G.9959)", "Zigbee 3.0 (IEEE 802.15.4)", "Matter (as converged transport)"],
    },
    {
        "name": "Radio Broadcast (FSK / DTMF over RF)",
        "category": "non_web",
        "medium": "radio_licensed_subghz",
        "description": "Use licensed/sub-licensed radio (UHF/VHF) to send FSK or DTMF-modulated commands to edge devices. Traditional SCADA approach for oil/gas/water infrastructure.",
        "protocols": ["FSK", "GMSK", "DTMF over RF", "MDC-1200"],
        "latency": "<500ms",
        "bandwidth": "1.2-9.6 Kbps typical",
        "range": "5-50 km (line-of-sight dependent)",
        "reliability": "Medium (env dependent, interference, multi-path)",
        "security": "None inherently; add AES via encryption radios (Motorola AES-256, etc.)",
        "complexity": "High",
        "cost": "Medium-High (licensed radio $1000-5000, license fees, antenna infrastructure)",
        "use_case": "Pipeline valve control, electrical substation switching, water system actuation where IP/cellular unavailable",
        "pros": [
            "Works where no IP or cellular exists",
            "Proven in industrial SCADA for decades",
            "Licensed spectrum provides interference protection",
            "Range up to 50km line-of-sight",
        ],
        "cons": [
            "Requires radio license in most countries",
            "License spectrum costs and regulatory paperwork",
            "No inherent security; encryption adds cost and complexity",
            "Susceptible to interference, weather, multi-path",
            "Low data rate (voice-band FSK)",
        ],
        "standards": ["ETSI EN 300 113", "FCC Part 90", "ITU-R SM.328"],
    },
    {
        "name": "Satellite IoT (Iridium SBD, Globalstar, Starlink Direct-to-Cell)",
        "category": "non_web",
        "medium": "satellite",
        "description": "Send commands to edge devices via satellite IoT networks. Iridium Short Burst Data (SBD) provides global pole-to-pole coverage. Emerging LEO direct-to-cell services.",
        "protocols": ["Iridium SBD", "Globalstar STX-3", "LoRaWAN via Sat (EchoStar)", "NB-IoT NTN"],
        "latency": "10-60 seconds (Iridium SBD), <1s (Starlink D2C)",
        "bandwidth": "340 bytes per SBD message (Iridium)",
        "range": "Global (Iridium), Regional (Globalstar, Inmarsat)",
        "reliability": "High (but dependent on sky view)",
        "security": "AES-256 (Iridium), end-to-end encryption supported",
        "complexity": "Medium-High",
        "cost": "Medium-High ($0.05-1.00 per message, module $100-500)",
        "use_case": "Edge devices in polar regions, oceans, deserts, or anywhere with zero terrestrial connectivity",
        "pros": [
            "True global coverage (Iridium covers poles)",
            "No terrestrial infrastructure needed",
            "Ideal for remote monitoring and command",
            "New LEO services (Starlink D2C) will reduce latency and cost",
        ],
        "cons": [
            "High per-message cost for traditional satellite IoT",
            "Iridium SBD has 10-60 second latency",
            "Requires clear sky view (not for indoor)",
            "Module cost higher than cellular/LoRaWAN",
            "Bandwidth extremely limited",
        ],
        "standards": ["Iridium SBD (9602/9603)", "3GPP Rel-17 NTN", "ITU-R M.1850"],
    },
    {
        "name": "Ethernet P2P (Broadcast / UDP Multicast)",
        "category": "web",
        "medium": "ethernet_wire",
        "description": "Direct Ethernet frame transmission using UDP broadcast or multicast on LAN segment. Edge devices listen on specific port and execute commands from any sender on the same subnet.",
        "protocols": ["UDP", "EtherType", "ARP", "IGMP"],
        "latency": "<1ms on LAN",
        "bandwidth": "Minimal (64 bytes minimum Ethernet frame)",
        "reliability": "Low-Medium (UDP no ACK, no delivery guarantee)",
        "security": "None at link layer; VLAN ACLs, MAC filtering optional",
        "complexity": "Low",
        "cost": "Very Low",
        "use_case": "Sub-millisecond relay triggering on local LAN, broadcast paging, synchronized actuation across multiple edge devices",
        "pros": [
            "Lowest possible latency on Ethernet (<1ms)",
            "Broadcast reaches all devices on subnet simultaneously",
            "No IP configuration needed (raw Ethernet frames)",
            "Works on the most basic microcontrollers with Ethernet PHY",
        ],
        "cons": [
            "No delivery guarantee (UDP best-effort)",
            "Broadcast storms can impact network performance",
            "No security or authentication by default",
            "Does not route across subnets",
            "Very implementation-specific; no standard API",
        ],
        "standards": ["IEEE 802.3", "RFC 768 (UDP)"],
    },
    {
        "name": "DTMF over VoIP (RFC 4733)",
        "category": "web",
        "medium": "ethernet_ip",
        "description": "Use RFC 4733 out-of-band DTMF event packets within a SIP RTP stream to relay keypad digits as commands. Each digit maps to a specific action on the edge device.",
        "protocols": ["SIP", "RTP", "RFC 4733", "RFC 2833"],
        "latency": "<50ms (same as voice RTP)",
        "bandwidth": "~100 bytes per DTMF event (within existing RTP stream)",
        "reliability": "High (redundant event reporting, duration field)",
        "security": "Same as SIP/RTP call (TLS + SRTP)",
        "complexity": "Medium",
        "cost": "Very Low (piggybacks on existing VoIP call)",
        "use_case": "Legacy IVR/auto-attendant style control over VoIP: press 1=relay on, press 2=relay off, press 3=query status",
        "pros": [
            "Piggybacks on existing SIP/VoIP infrastructure",
            "Industry standard for DTMF transport over IP",
            "Backward compatible with older PSTN DTMF patterns",
            "Out-of-band avoids voice codec distortion",
        ],
        "cons": [
            "Edge device must be an RTP endpoint or media proxy",
            "Requires active SIP call/session to send DTMF",
            "Limited command vocabulary (0-9, *, #)",
            "Not for high-frequency commands (single DTMF per packet)",
        ],
        "standards": ["RFC 4733", "RFC 2833"],
    },
    {
        "name": "DNP3 / IEC 61850 (for utility/SCADA)",
        "category": "non_web",
        "medium": "serial_ethernet",
        "description": "Industrial SCADA protocols (DNP3 over TCP/UDP, IEC 61850 over Ethernet) designed for electrical substation and utility edge device command/control.",
        "protocols": ["DNP3", "IEC 61850", "IEC 60870-5-101/104", "MODBUS TCP"],
        "latency": "<10ms on LAN",
        "bandwidth": "Minimal (binary commands, analog status)",
        "reliability": "Very High (time-tagged, sequence-of-events, redundant links)",
        "security": "DNP3 Secure Authentication (SAv5), IEC 62351",
        "complexity": "Very High",
        "cost": "High (SCADA master license, RTU, engineering)",
        "use_case": "Utility substation, electrical grid, water treatment plant edge device command/control (relay, breaker, valve)",
        "pros": [
            "Industrial-grade reliability and determinism",
            "Time-stamped events for post-incident analysis",
            "Standard in utility industry worldwide",
            "Secure authentication profiles available (SAv5)",
        ],
        "cons": [
            "Very high complexity and engineering cost",
            "Not designed for commercial/office environment",
            "Overkill for simple relay/command use cases",
            "Requires trained SCADA engineers",
            "IEC 61850 requires specific Ethernet switches (GOOSE messaging)",
        ],
        "standards": ["IEEE 1815 (DNP3)", "IEC 61850", "IEC 62351", "IEEE C37.118"],
    },
    {
        "name": "NB-IoT / LTE-M",
        "category": "non_web",
        "medium": "cellular_lpwans",
        "description": "Low-power cellular IoT technologies for command and telemetry where licensed-carrier coverage is available.",
        "protocols": ["NB-IoT", "LTE-M", "MQTT", "CoAP", "LwM2M"],
        "latency": "100ms to several seconds",
        "bandwidth": "Tens to hundreds of Kbps",
        "range": "Carrier footprint, strong indoor penetration",
        "reliability": "High where carrier IoT coverage exists",
        "security": "3GPP SIM authentication, LTE encryption, TLS at application layer",
        "complexity": "Medium",
        "cost": "Low-Medium subscription",
        "use_case": "Remote alarms, utility meters, building edge controllers with small data payloads",
        "pros": [
            "Carrier-managed licensed spectrum",
            "Better building penetration than classic LTE",
            "Lower power than full cellular modems",
        ],
        "cons": [
            "Coverage varies by country and operator",
            "Downlink latency can be variable",
            "Requires SIM/eSIM lifecycle management",
        ],
        "standards": ["3GPP LTE Cat-M1", "3GPP NB-IoT", "LwM2M"],
    },
    {
        "name": "eSIM / Remote SIM Provisioning for IoT",
        "category": "non_web",
        "medium": "cellular_esim",
        "description": "Use eSIM/eUICC profiles and remote SIM provisioning platforms to keep edge devices connected across carriers without physical SIM swaps.",
        "protocols": ["eSIM", "eUICC", "SGP.02", "SGP.22", "SGP.32", "HTTPS APIs"],
        "latency": "Carrier/data-path dependent",
        "bandwidth": "Cellular plan dependent",
        "range": "Multi-carrier national or global footprint",
        "reliability": "High with multi-IMSI/multi-carrier failover",
        "security": "eUICC profile security, carrier authentication, TLS API control plane",
        "complexity": "Medium-High",
        "cost": "Low-Medium per active profile/device",
        "use_case": "Cellular command path for remote PBX gateways, alarms, meters, kiosks, fleet equipment, and industrial edge controllers",
        "pros": [
            "No truck roll for physical SIM swaps",
            "Supports carrier failover and regional profile changes",
            "API-managed fleet lifecycle",
        ],
        "cons": [
            "Device modem/eUICC compatibility must be verified",
            "Carrier roaming and permanent-roaming rules vary by country",
            "Voice/SMS support differs from data-only IoT plans",
        ],
        "standards": ["GSMA SGP.02", "GSMA SGP.22", "GSMA SGP.32"],
    },
    {
        "name": "Private LTE / Private 5G",
        "category": "non_web",
        "medium": "private_cellular",
        "description": "Dedicated campus cellular network for mission-critical voice-adjacent device control and mobile edge connectivity.",
        "protocols": ["LTE", "5G NR", "SIP", "MQTT", "HTTPS"],
        "latency": "5-30ms typical",
        "bandwidth": "Mbps to Gbps",
        "range": "Campus or facility",
        "reliability": "Very High with engineered RF design",
        "security": "SIM/eSIM authentication, 5G AKA, network slicing, private core policy",
        "complexity": "Very High",
        "cost": "High",
        "use_case": "Hospitals, ports, factories, airports, mines, and public safety campuses",
        "pros": [
            "Controlled RF and QoS",
            "Mobility support beyond Wi-Fi",
            "Can carry voice, video, and control traffic",
        ],
        "cons": [
            "Spectrum and core-network expertise required",
            "High deployment cost",
            "Regulatory model differs by country",
        ],
        "standards": ["3GPP 4G LTE", "3GPP 5G NR"],
    },
    {
        "name": "Matter over Thread",
        "category": "non_web",
        "medium": "radio_802_15_4",
        "description": "IP-based smart-building control using Matter application semantics over Thread low-power mesh.",
        "protocols": ["Matter", "Thread", "IPv6", "CoAP"],
        "latency": "<100ms typical",
        "bandwidth": "250 Kbps PHY",
        "range": "Building mesh",
        "reliability": "High in dense mesh",
        "security": "Matter device attestation, CASE, AES-CCM",
        "complexity": "Medium",
        "cost": "Low-Medium",
        "use_case": "PBX-triggered building devices such as locks, lights, relays, and sensors",
        "pros": [
            "Modern multi-vendor smart-building standard",
            "IP-based, unlike many older home automation stacks",
            "Strong onboarding and attestation model",
        ],
        "cons": [
            "Still maturing in commercial deployments",
            "Needs border routers",
            "Device-class coverage is not universal",
        ],
        "standards": ["Matter 1.x", "Thread 1.3", "IEEE 802.15.4"],
    },
    {
        "name": "Bluetooth LE / BLE Mesh",
        "category": "non_web",
        "medium": "radio_24ghz",
        "description": "Short-range wireless control using BLE GATT services or BLE Mesh models.",
        "protocols": ["Bluetooth LE", "GATT", "BLE Mesh"],
        "latency": "10-200ms",
        "bandwidth": "125 Kbps to 2 Mbps PHY",
        "range": "10-100m per hop",
        "reliability": "Medium-High",
        "security": "LE Secure Connections, AES-CCM, provisioning keys",
        "complexity": "Medium",
        "cost": "Very Low",
        "use_case": "Phone-proximate setup, room devices, badges, small relays, and sensors",
        "pros": [
            "Available in phones and low-cost microcontrollers",
            "Good for provisioning and local control",
            "BLE Mesh supports managed building-scale networks",
        ],
        "cons": [
            "2.4GHz interference",
            "Range is limited without mesh",
            "Gateway needed for remote PBX integration",
        ],
        "standards": ["Bluetooth Core", "Bluetooth Mesh Profile"],
    },
    {
        "name": "Wi-Fi HaLow (802.11ah)",
        "category": "non_web",
        "medium": "radio_subghz",
        "description": "Sub-GHz Wi-Fi variant for longer-range low-power IP connectivity to edge devices.",
        "protocols": ["IEEE 802.11ah", "IPv4", "IPv6", "HTTPS", "MQTT"],
        "latency": "10-100ms",
        "bandwidth": "Hundreds of Kbps to Mbps",
        "range": "Hundreds of meters to 1km+",
        "reliability": "Medium-High",
        "security": "WPA3 where supported, TLS at application layer",
        "complexity": "Medium",
        "cost": "Medium",
        "use_case": "Large campuses, warehouses, agriculture, and parking facilities needing IP without cellular",
        "pros": [
            "Native IP model like Wi-Fi",
            "Better range and wall penetration than 2.4GHz Wi-Fi",
            "Supports many IoT devices per access point",
        ],
        "cons": [
            "Ecosystem is younger than Wi-Fi 6/7 or LoRaWAN",
            "Regional sub-GHz spectrum differs",
            "Client hardware choices are narrower",
        ],
        "standards": ["IEEE 802.11ah"],
    },
    {
        "name": "RS-485 / Modbus RTU",
        "category": "non_web",
        "medium": "serial_wire",
        "description": "Differential serial bus for robust local wired control of relays, PLCs, and I/O modules.",
        "protocols": ["RS-485", "Modbus RTU"],
        "latency": "<20ms local",
        "bandwidth": "9.6 Kbps to 115.2 Kbps typical",
        "range": "Up to 1200m bus length",
        "reliability": "High in electrically noisy sites",
        "security": "None natively; physical security and gateway isolation",
        "complexity": "Low-Medium",
        "cost": "Very Low",
        "use_case": "PBX-to-gateway command of industrial relay boards and legacy building devices",
        "pros": [
            "Very cheap and rugged",
            "Long cable runs",
            "Huge ecosystem of relay and sensor modules",
        ],
        "cons": [
            "No native encryption or authentication",
            "Bus termination and addressing must be correct",
            "Gateway needed for IP/cloud integration",
        ],
        "standards": ["TIA/EIA-485", "Modbus RTU"],
    },
    {
        "name": "Dry Contact / Relay Closure",
        "category": "non_web",
        "medium": "electrical_contact",
        "description": "Simple electrically isolated contact closure that emulates a button, alarm input, or door-strike trigger.",
        "protocols": ["GPIO", "Relay", "Opto-isolated input"],
        "latency": "<5ms",
        "bandwidth": "Binary on/off",
        "range": "Cable dependent",
        "reliability": "Very High when wired correctly",
        "security": "Physical security only",
        "complexity": "Very Low",
        "cost": "Very Low",
        "use_case": "Door release, paging amplifier trigger, siren activation, elevator/fire-panel interface",
        "pros": [
            "Universally understood by legacy equipment",
            "No protocol compatibility issue",
            "Fails visibly and is easy to test with a meter",
        ],
        "cons": [
            "No identity, encryption, or audit trail by itself",
            "Only carries simple binary state",
            "Requires local wiring and electrical protection",
        ],
        "standards": ["IEC relay practice", "GPIO vendor specs"],
    },
    {
        "name": "Power Line Communication (PLC)",
        "category": "non_web",
        "medium": "powerline",
        "description": "Send control data over existing electrical wiring using narrowband or broadband PLC.",
        "protocols": ["G3-PLC", "PRIME", "HomePlug Green PHY"],
        "latency": "10ms to seconds",
        "bandwidth": "Kbps to Mbps",
        "range": "Building or utility segment",
        "reliability": "Medium",
        "security": "AES profiles vary by standard",
        "complexity": "High",
        "cost": "Medium",
        "use_case": "Utility meters, building devices, and retrofit sites where new signal cabling is hard",
        "pros": [
            "Uses existing power wiring",
            "Useful in dense retrofit environments",
            "Mature in smart-meter deployments",
        ],
        "cons": [
            "Noise and phase coupling affect reliability",
            "Installation rules vary by electrical system",
            "Not a good fit for life-safety triggers without engineering",
        ],
        "standards": ["G3-PLC", "PRIME", "HomePlug Green PHY"],
    },
]

# --- Technical enrichment ---

TECH_CAPABILITIES = {
    "sip_stack": ["SIP", "SIP INFO", "SIP NOTIFY"],
    "webrtc": ["WebRTC", "Data Channel", "ICE"],
    "rest_api": ["REST", "HTTP", "HTTPS", "API"],
    "mqtt": ["MQTT", "pub/sub"],
    "low_power_wireless": ["LoRaWAN", "Z-Wave", "Zigbee"],
    "cellular": ["GSM", "4G", "LTE", "5G", "SMS"],
    "satellite": ["Iridium", "Satellite", "SBD"],
    "udp_broadcast": ["UDP", "Broadcast", "Multicast"],
    "scada_suite": ["DNP3", "IEC 61850", "MODBUS", "SCADA"],
}


def score_protocol_richness(tags: list[str]) -> int:
    score = 0
    all_tags = " ".join(t.lower() for t in tags)
    for capability, keywords in TECH_CAPABILITIES.items():
        if any(k.lower() in all_tags for k in keywords):
            score += 1
    return score


def score_security_posture(sol: dict) -> int:
    score = 0
    tags = " ".join(sol.get("tags", []))
    pros = " ".join(sol.get("pros", []))
    text = (tags + " " + pros).lower()
    if "tls" in text:
        score += 2
    if "srtp" in text:
        score += 2
    if "aes" in text:
        score += 2
    if "mfa" in text or "multifactor" in text or "multi-factor" in text:
        score += 1
    if "oauth" in text:
        score += 1
    if "mtls" in text:
        score += 1
    if "end-to-end" in text:
        score += 2
    return min(score, 10)


# --- Enrich registry with technical metadata ---


def enrich_registry(
    registry_df: pd.DataFrame,
    output_path: Optional[str] = "data/processed/tech_enriched_registry.csv",
) -> pd.DataFrame:
    """Add technical metadata columns to the product researcher's registry output."""
    df = registry_df.copy()
    if "tags" in df.columns:
        df["protocol_richness"] = df["tags"].apply(
            lambda t: score_protocol_richness(str(t).split(", "))
        )
    df["security_score"] = df.apply(score_security_posture, axis=1)
    if output_path is not None and len(df):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
    return df


# --- Awesome list generation ---

ALT_RESOURCE_URLS = {
    "SIP INFO / REFER": "https://www.rfc-editor.org/rfc/rfc2976",
    "REST API (HTTP/HTTPS)": "https://developer.mozilla.org/en-US/docs/Web/HTTP",
    "WebSocket (wss://)": "https://www.rfc-editor.org/rfc/rfc6455",
    "MQTT (MQTT-SN)": "https://mqtt.org/",
    "WebRTC Data Channel": "https://www.w3.org/TR/webrtc/",
    "gRPC (HTTP/2)": "https://grpc.io/docs/",
    "CoAP (Constrained Application Protocol)": "https://www.rfc-editor.org/rfc/rfc7252",
    "GraphQL API / Subscriptions": "https://graphql.org/",
    "Webhook Callback": "https://github.com/standard-webhooks/standard-webhooks",
    "AMQP / RabbitMQ": "https://www.rabbitmq.com/tutorials/amqp-concepts",
    "NATS / JetStream": "https://docs.nats.io/",
    "OPC UA": "https://opcfoundation.org/about/opc-technologies/opc-ua/",
    "Modbus TCP": "https://modbus.org/specs.php",
    "LoRaWAN": "https://lora-alliance.org/about-lorawan/",
    "SMS / GSM AT Commands": "https://www.3gpp.org/",
    "Z-Wave / Zigbee": "https://csa-iot.org/all-solutions/zigbee/",
    "Radio Broadcast (FSK / DTMF over RF)": "https://www.itu.int/rec/R-REC-SM.328/",
    "Satellite IoT (Iridium SBD, Globalstar, Starlink Direct-to-Cell)": "https://www.iridium.com/services/iridium-sbd/",
    "Ethernet P2P (Broadcast / UDP Multicast)": "https://www.rfc-editor.org/rfc/rfc768",
    "DTMF over VoIP (RFC 4733)": "https://www.rfc-editor.org/rfc/rfc4733",
    "DNP3 / IEC 61850 (for utility/SCADA)": "https://www.dnp.org/About/Overview-of-DNP3-Protocol",
    "NB-IoT / LTE-M": "https://www.gsma.com/solutions-and-impact/technologies/internet-of-things/narrow-band-internet-of-things-nb-iot/",
    "eSIM / Remote SIM Provisioning for IoT": "https://www.gsma.com/solutions-and-impact/technologies/esim/",
    "Private LTE / Private 5G": "https://www.3gpp.org/technologies/private-networks",
    "Matter over Thread": "https://csa-iot.org/all-solutions/matter/",
    "Bluetooth LE / BLE Mesh": "https://www.bluetooth.com/learn-about-bluetooth/feature-enhancements/mesh/",
    "Wi-Fi HaLow (802.11ah)": "https://www.wi-fi.org/discover-wi-fi/wi-fi-halow",
    "RS-485 / Modbus RTU": "https://modbus.org/specs.php",
    "Dry Contact / Relay Closure": "https://en.wikipedia.org/wiki/Dry_contact",
    "Power Line Communication (PLC)": "https://www.itu.int/en/ITU-T/studygroups/2017-2020/15/Pages/g.hn.aspx",
}


def _alternative_device_range(alt: dict) -> str:
    text = f"{alt.get('name', '')} {alt.get('medium', '')} {alt.get('use_case', '')}".lower()
    if any(k in text for k in ["satellite", "lorawan", "nb-iot", "lte-m", "private lte", "private 5g", "cellular", "esim"]):
        return "100-100,000 remote devices"
    if any(k in text for k in ["scada", "dnp3", "iec 61850", "opc ua", "modbus"]):
        return "10-10,000 industrial points"
    if any(k in text for k in ["rs-485", "dry contact", "relay"]):
        return "1-256 local I/O points"
    if any(k in text for k in ["zigbee", "z-wave", "thread", "ble", "matter"]):
        return "10-1,000 building devices"
    if any(k in text for k in ["api", "webhook", "grpc", "mqtt", "amqp", "nats"]):
        return "100-1,000,000 endpoints/events"
    return "5-5,000 devices"


def _alternative_industries(alt: dict) -> str:
    text = f"{alt.get('name', '')} {alt.get('medium', '')} {alt.get('use_case', '')} {alt.get('description', '')}".lower()
    industries = []
    if any(k in text for k in ["utility", "scada", "substation", "water", "power", "modbus", "opc"]):
        industries.extend(["Utilities", "Energy", "Water", "Industrial automation"])
    if any(k in text for k in ["building", "door", "lock", "lighting", "relay", "thread", "zigbee", "z-wave"]):
        industries.extend(["Smart building", "Facilities", "Hospitality", "Retail"])
    if any(k in text for k in ["satellite", "lorawan", "cellular", "nb-iot", "lte-m", "private 5g"]):
        industries.extend(["Logistics", "Agriculture", "Remote infrastructure", "Public safety"])
    if any(k in text for k in ["api", "webhook", "grpc", "webrtc", "sip", "dtmf"]):
        industries.extend(["SaaS", "Contact center", "Professional services", "Systems integration"])
    if not industries:
        industries = ["SMB", "Enterprise", "IoT"]
    return "; ".join(dict.fromkeys(industries))


def _alternative_cost_model(alt: dict) -> str:
    cost = alt.get("cost", "")
    text = f"{alt.get('name', '')} {alt.get('medium', '')}".lower()
    if any(k in text for k in ["satellite", "private lte", "private 5g", "scada", "iec 61850"]):
        return f"{cost}; high engineering/infrastructure"
    if any(k in text for k in ["sms", "cellular", "nb-iot", "lte-m", "lorawan"]):
        return f"{cost}; subscription or message/device fees"
    if any(k in text for k in ["api", "webhook", "grpc", "mqtt", "amqp", "nats"]):
        return f"{cost}; platform/broker plus usage"
    return cost


EXPANDED_ALTERNATIVE_SPECS = [
    ("SIP NOTIFY / SUBSCRIBE events", "web", "ethernet_ip", ["SIP", "SUBSCRIBE", "NOTIFY"], "https://www.rfc-editor.org/rfc/rfc6665", "Voice platform events trigger subscribed device actions.", "SaaS; Contact center; Systems integration"),
    ("SIP MESSAGE instant command", "web", "ethernet_ip", ["SIP MESSAGE", "CPIM"], "https://www.rfc-editor.org/rfc/rfc3428", "Short SIP text payloads carry commands to SIP-aware gateways.", "Facilities; Hospitality; Systems integration"),
    ("SIP KPML digit events", "web", "ethernet_ip", ["SIP", "KPML", "XML"], "https://www.rfc-editor.org/rfc/rfc4730", "Keypad markup events map phone digits to edge commands.", "Contact center; Hospitality; Legacy facilities"),
    ("RTP audio tone detection", "web", "ethernet_ip", ["RTP", "DSP", "Goertzel"], "https://www.rfc-editor.org/rfc/rfc3550", "Gateway detects tones or audio cues in a voice stream.", "Legacy facilities; Paging; Hospitality"),
    ("SRTP-secured media command channel", "web", "ethernet_ip", ["SRTP", "RTP", "SIP"], "https://www.rfc-editor.org/rfc/rfc3711", "Encrypted RTP session carries command tones or metadata.", "Enterprise; Government; Healthcare"),
    ("XMPP PubSub", "web", "ethernet_ip", ["XMPP", "PubSub", "TLS"], "https://xmpp.org/extensions/xep-0060.html", "Federated publish/subscribe events dispatch device commands.", "Enterprise; Messaging; Systems integration"),
    ("Redis Streams", "web", "ethernet_ip", ["Redis", "Streams", "TLS"], "https://redis.io/docs/latest/develop/data-types/streams/", "Append-only event stream with consumer groups for command workers.", "SaaS; Retail; IoT"),
    ("Apache Kafka", "web", "ethernet_ip", ["Kafka", "TLS", "SASL"], "https://kafka.apache.org/documentation/", "High-scale event log for auditable command workflows.", "Enterprise; Logistics; Financial services"),
    ("Pulsar topics", "web", "ethernet_ip", ["Apache Pulsar", "TLS"], "https://pulsar.apache.org/docs/", "Multi-tenant topic bus for command and telemetry streams.", "SaaS; IoT; Enterprise"),
    ("ZeroMQ command sockets", "web", "ethernet_ip", ["ZeroMQ", "TCP", "CurveZMQ"], "https://zeromq.org/", "Lightweight socket patterns connect local command agents.", "Industrial automation; Systems integration; Labs"),
    ("DDS / RTPS", "web", "ethernet_ip", ["DDS", "RTPS"], "https://www.omg.org/spec/DDS/", "Real-time pub/sub middleware for deterministic edge control.", "Robotics; Aerospace; Industrial automation"),
    ("LwM2M device management", "web", "ethernet_ip", ["LwM2M", "CoAP", "DTLS"], "https://omaspecworks.org/what-is-oma-specworks/iot/lightweight-m2m-lwm2m/", "Device-management objects expose execute commands and telemetry.", "Utilities; IoT; Remote infrastructure"),
    ("OMA DM legacy device management", "web", "cellular_ip", ["OMA DM", "HTTPS"], "https://omaspecworks.org/what-is-oma-specworks/device-management/", "Legacy mobile-device management channel for remote configuration.", "Telecom; Field devices; Legacy fleets"),
    ("SNMP SET command", "web", "ethernet_ip", ["SNMPv3", "UDP"], "https://www.rfc-editor.org/rfc/rfc3411", "Management station writes OIDs to trigger networked equipment.", "Telecom; Network operations; Facilities"),
    ("NETCONF over SSH", "web", "ethernet_ip", ["NETCONF", "SSH", "YANG"], "https://www.rfc-editor.org/rfc/rfc6241", "Structured network configuration RPCs operate routers and gateways.", "Telecom; Data centers; Enterprise networks"),
    ("RESTCONF", "web", "ethernet_ip", ["RESTCONF", "YANG", "HTTPS"], "https://www.rfc-editor.org/rfc/rfc8040", "HTTP-based YANG control for network and gateway devices.", "Telecom; Enterprise networks; Data centers"),
    ("OpenFlow SDN control", "web", "ethernet_ip", ["OpenFlow", "TLS"], "https://opennetworking.org/sdn-resources/openflow/", "SDN controller changes paths or port state after voice events.", "Data centers; Telecom; Campus networks"),
    ("BACnet/IP", "web", "ethernet_ip", ["BACnet/IP", "UDP"], "https://bacnet.org/", "Building automation objects control HVAC, access, and alarms.", "Smart building; Facilities; Healthcare"),
    ("KNXnet/IP", "web", "ethernet_ip", ["KNX", "KNXnet/IP"], "https://www.knx.org/knx-en/for-professionals/What-is-KNX/", "Building bus integration over IP for lighting and relay actions.", "Smart building; Hospitality; Facilities"),
    ("DALI-2 lighting control", "non_web", "building_bus", ["DALI-2", "IEC 62386"], "https://www.dali-alliance.org/dali/", "Dedicated lighting bus receives commands through a gateway.", "Smart building; Retail; Hospitality"),
    ("DMX512 / RDM", "non_web", "serial_wire", ["DMX512", "RDM", "RS-485"], "https://tsp.esta.org/tsp/documents/published_docs.php", "Lighting and stage-control bus triggers scenes and relays.", "Venues; Hospitality; Retail"),
    ("CAN bus / CANopen", "non_web", "fieldbus", ["CAN", "CANopen"], "https://www.can-cia.org/can-knowledge/canopen", "Robust fieldbus commands controllers and mobile equipment.", "Industrial automation; Vehicles; Robotics"),
    ("J1939 vehicle bus", "non_web", "fieldbus", ["SAE J1939", "CAN"], "https://www.sae.org/standards/content/j1939_202208/", "Heavy-vehicle network commands and reads equipment state.", "Fleet; Logistics; Agriculture"),
    ("PROFINET IO", "web", "ethernet_ip", ["PROFINET", "Industrial Ethernet"], "https://www.profibus.com/technology/profinet", "Industrial Ethernet I/O commands PLC devices in factories.", "Manufacturing; Industrial automation; Utilities"),
    ("PROFIBUS DP", "non_web", "fieldbus", ["PROFIBUS DP", "RS-485"], "https://www.profibus.com/technology/profibus", "Legacy factory fieldbus controls distributed I/O and drives.", "Manufacturing; Legacy factories; Utilities"),
    ("EtherNet/IP CIP", "web", "ethernet_ip", ["EtherNet/IP", "CIP"], "https://www.odva.org/technology-standards/key-technologies/ethernet-ip/", "CIP messages control PLCs, drives, and industrial I/O.", "Manufacturing; Warehousing; Industrial automation"),
    ("EtherCAT", "web", "ethernet_wire", ["EtherCAT"], "https://www.ethercat.org/en/technology.html", "Deterministic Ethernet fieldbus for fast machine control.", "Robotics; Manufacturing; Motion control"),
    ("SERCOS III", "web", "ethernet_wire", ["SERCOS III"], "https://www.sercos.org/technology/sercos-iii/", "Industrial real-time Ethernet for motion and machine commands.", "Motion control; Manufacturing; Robotics"),
    ("IO-Link", "non_web", "sensor_bus", ["IO-Link", "IEC 61131-9"], "https://io-link.com/en/Technology/what_is_IO-Link.php", "Point-to-point sensor/actuator commands through IO-Link masters.", "Manufacturing; Packaging; Machine builders"),
    ("1-Wire control bus", "non_web", "serial_wire", ["1-Wire"], "https://www.analog.com/en/resources/technical-articles/guide-to-1wire-communication.html", "Very low-cost single-wire sensor and switch control.", "Facilities; Labs; Low-cost monitoring"),
    ("I2C local device bus", "non_web", "board_bus", ["I2C"], "https://www.nxp.com/docs/en/user-guide/UM10204.pdf", "Local microcontroller bus controls nearby I/O expanders.", "Embedded systems; Kiosks; Edge gateways"),
    ("SPI local device bus", "non_web", "board_bus", ["SPI"], "https://developer.arm.com/documentation/102159/0100/Serial-Peripheral-Interface--SPI-", "Fast board-level bus controls local peripherals and relays.", "Embedded systems; Industrial gateways; Hardware products"),
    ("GPIO direct digital output", "non_web", "electrical_contact", ["GPIO"], "https://www.raspberrypi.com/documentation/computers/raspberry-pi.html", "Controller toggles a digital pin wired to an opto-isolated input.", "Facilities; Kiosks; Industrial gateways"),
    ("Open collector / open drain output", "non_web", "electrical_contact", ["Open collector", "Open drain"], "https://en.wikipedia.org/wiki/Open_collector", "Sink-output interface triggers alarms, buzzers, and relay boards.", "Security; Alarms; Legacy equipment"),
    ("Wiegand access-control interface", "non_web", "access_control", ["Wiegand"], "https://www.securityindustry.org/industry-standards/open-supervised-device-protocol/", "Access-control gateway bridges PBX events to door controllers.", "Access control; Facilities; Healthcare"),
    ("OSDP secure access control", "non_web", "access_control", ["OSDP", "RS-485", "AES"], "https://www.securityindustry.org/industry-standards/open-supervised-device-protocol/", "Supervised encrypted RS-485 protocol for readers and doors.", "Access control; Government; Enterprise"),
    ("Alarm Contact ID over IP gateway", "web", "ethernet_ip", ["SIA DC-09", "Contact ID"], "https://www.siaonline.org/what-we-do/standards/", "Alarm events are translated into IP receiver messages.", "Security; Monitoring centers; Facilities"),
    ("SIA DC-09 alarm signaling", "web", "ethernet_ip", ["SIA DC-09", "TCP", "UDP"], "https://www.siaonline.org/what-we-do/standards/", "Standardized alarm-over-IP path replaces dial-up alarm lines.", "Security; Insurance; Monitoring centers"),
    ("CAP common alerting protocol", "web", "ethernet_ip", ["CAP", "XML", "HTTPS"], "https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html", "Emergency alerts fan out to sirens, paging, and displays.", "Public safety; Government; Campuses"),
    ("EAS / SAME alert relay", "non_web", "radio_broadcast", ["SAME", "EAS"], "https://www.weather.gov/nwr/same", "Broadcast alert codes trigger local warning equipment.", "Public safety; Broadcast; Campuses"),
    ("POCSAG paging", "non_web", "radio_paging", ["POCSAG"], "https://www.etsi.org/deliver/etsi_en/300200_300299/300224/", "One-way paging messages activate staff or device workflows.", "Healthcare; Public safety; Hospitality"),
    ("FLEX paging", "non_web", "radio_paging", ["FLEX"], "https://www.etsi.org/", "High-capacity paging protocol for one-way alert command paths.", "Healthcare; Public safety; Industrial sites"),
    ("TETRA SDS messaging", "non_web", "licensed_radio", ["TETRA", "SDS"], "https://www.etsi.org/technologies/tetra", "Mission-critical radio short data service sends commands.", "Public safety; Utilities; Transportation"),
    ("DMR data / text messaging", "non_web", "licensed_radio", ["DMR", "ETSI TS 102 361"], "https://www.etsi.org/technologies/digital-mobile-radio", "Digital mobile radio data packets command remote units.", "Security; Facilities; Utilities"),
    ("P25 data messaging", "non_web", "licensed_radio", ["Project 25", "P25"], "https://www.apcointl.org/spectrum-management/p25/", "Public-safety radio data path for critical control messages.", "Public safety; Government; Utilities"),
    ("Wi-SUN FAN", "non_web", "radio_subghz_mesh", ["Wi-SUN", "IPv6", "6LoWPAN"], "https://wi-sun.org/technology/", "Utility-grade sub-GHz IPv6 mesh for field devices.", "Utilities; Smart city; Street lighting"),
    ("6LoWPAN mesh", "non_web", "radio_802_15_4", ["6LoWPAN", "IPv6"], "https://www.rfc-editor.org/rfc/rfc4944", "IPv6 packets run over low-power IEEE 802.15.4 mesh.", "IoT; Smart building; Agriculture"),
    ("Wireless M-Bus", "non_web", "radio_subghz", ["Wireless M-Bus", "EN 13757"], "https://www.oms-group.org/en/about-oms/technology/", "Metering radio protocol for utility and building telemetry.", "Utilities; Smart metering; Facilities"),
    ("Sigfox / ultra-narrowband IoT", "non_web", "radio_unb", ["Sigfox", "UNB"], "https://build.sigfox.com/", "Ultra-narrowband low-power messages for simple remote triggers.", "Logistics; Agriculture; Asset tracking"),
    ("Mioty telegram splitting", "non_web", "radio_lpwans", ["mioty", "TS-UNB"], "https://mioty-alliance.com/technology/", "Robust LPWAN telegram splitting for dense industrial sensing.", "Industrial IoT; Utilities; Smart city"),
    ("DECT-ULE", "non_web", "radio_dect", ["DECT-ULE"], "https://www.ulealliance.org/", "Low-power DECT-based building device control.", "Smart building; Healthcare; Hospitality"),
    ("Wi-Fi Aware / NAN", "non_web", "wifi_direct", ["Wi-Fi Aware", "NAN"], "https://www.wi-fi.org/discover-wi-fi/wi-fi-aware", "Nearby devices discover and command each other without AP setup.", "Retail; Facilities; Mobile workflows"),
    ("Wi-Fi Direct", "non_web", "wifi_direct", ["Wi-Fi Direct"], "https://www.wi-fi.org/discover-wi-fi/wi-fi-direct", "Peer-to-peer Wi-Fi link for local command panels.", "Kiosks; Field service; Facilities"),
    ("NFC tap trigger", "non_web", "near_field", ["NFC", "ISO 14443"], "https://nfc-forum.org/learn/specifications/", "Phone or tag tap starts authenticated local command workflow.", "Access control; Retail; Field service"),
    ("RFID reader event trigger", "non_web", "near_field", ["RFID", "EPC Gen2"], "https://www.gs1.org/standards/epc-rfid", "Reader events trigger doors, conveyors, or call workflows.", "Logistics; Warehousing; Retail"),
    ("UWB ranging trigger", "non_web", "radio_uwb", ["UWB", "IEEE 802.15.4z"], "https://www.firaconsortium.org/discover/specifications", "Precise location/ranging events trigger local actions.", "Healthcare; Warehousing; Secure access"),
    ("GNSS geofence trigger", "non_web", "satellite_navigation", ["GNSS", "GPS"], "https://www.gps.gov/systems/gps/", "Device position crossing a geofence initiates command workflows.", "Fleet; Logistics; Field service"),
    ("Cell broadcast command alert", "non_web", "cellular_broadcast", ["Cell Broadcast", "3GPP"], "https://www.3gpp.org/specifications-technologies/specifications-by-series", "One-to-many cellular broadcast reaches many devices in an area.", "Public safety; Telecom; Critical alerts"),
    ("USSD session command", "non_web", "cellular", ["USSD", "GSM"], "https://www.3gpp.org/", "Interactive carrier session carries short command choices.", "Telecom; Field operations; Emerging markets"),
    ("IMS data channel", "web", "cellular_ip", ["IMS", "RCS", "SIP"], "https://www.gsma.com/solutions-and-impact/technologies/networks/rcs/", "Carrier IMS/RCS channel carries rich command interactions.", "Telecom; Contact center; Consumer services"),
    ("RCS business messaging trigger", "web", "cellular_ip", ["RCS", "RBM"], "https://www.gsma.com/solutions-and-impact/technologies/networks/rcs/", "Verified business messages trigger workflows via rich actions.", "Retail; Contact center; Field service"),
    ("Email-to-command parser", "web", "internet_mail", ["SMTP", "IMAP", "DKIM"], "https://www.rfc-editor.org/rfc/rfc5321", "Signed email messages are parsed into low-urgency commands.", "SMB; Facilities; Maintenance"),
    ("SFTP drop-file command", "web", "ethernet_ip", ["SFTP", "SSH"], "https://www.openssh.com/manual.html", "A watched secure file drop converts batch files into commands.", "Manufacturing; Finance; Legacy integration"),
    ("MQTT over WebSocket", "web", "ethernet_ip", ["MQTT", "WebSocket"], "https://mqtt.org/", "Browser/cloud friendly MQTT transport over standard web ports.", "IoT; SaaS; Smart building"),
    ("OPC UA PubSub over MQTT", "web", "ethernet_ip", ["OPC UA PubSub", "MQTT"], "https://opcfoundation.org/about/opc-technologies/opc-ua/", "Industrial semantic messages ride MQTT brokers.", "Manufacturing; Industrial IoT; Utilities"),
    ("Digital input over IP I/O module", "web", "ethernet_ip", ["HTTP", "Modbus TCP", "SNMP"], "https://www.moxa.com/en/products/industrial-edge-connectivity/controllers-and-ios/universal-controllers-and-i-os", "Network I/O module maps IP commands to relay outputs.", "Facilities; Industrial automation; Retail"),
    ("USB HID control relay", "non_web", "usb", ["USB HID"], "https://www.usb.org/hid", "Host toggles USB relay as a local device command.", "Kiosks; Labs; Prototyping"),
    ("Serial RS-232 command", "non_web", "serial_wire", ["RS-232"], "https://tiaonline.org/what-we-do/standards/", "Legacy equipment receives ASCII commands over serial.", "Hospitality; AV; Legacy facilities"),
    ("HDMI-CEC device command", "non_web", "av_bus", ["HDMI-CEC"], "https://hdmi.org/spec/index", "Telephony events control displays and AV equipment.", "Hospitality; Meeting rooms; Digital signage"),
    ("Infrared blaster", "non_web", "infrared", ["IR", "NEC", "RC-5"], "https://en.wikipedia.org/wiki/Consumer_IR", "Gateway emits remote-control IR codes to legacy devices.", "Hospitality; AV; Retail"),
    ("Visible/audible tone sensor", "non_web", "sensor_trigger", ["Audio", "Optical"], "https://www.iso.org/standard/72361.html", "Sensor detects buzzer/light state and triggers integration.", "Legacy facilities; Safety retrofits; Maintenance"),
    ("Computer vision event trigger", "web", "edge_ai", ["RTSP", "ONVIF", "AI inference"], "https://www.onvif.org/profiles/profile-t/", "Camera analytics convert visual events into commands.", "Security; Retail; Manufacturing"),
    ("ONVIF event service", "web", "ethernet_ip", ["ONVIF", "SOAP", "WS-Eventing"], "https://www.onvif.org/profiles/profile-t/", "Video/security device events trigger PBX or edge actions.", "Security; Facilities; Retail"),
    ("PTP time-synchronized command", "web", "ethernet_wire", ["IEEE 1588 PTP"], "https://standards.ieee.org/ieee/1588/6825/", "Time-aligned command execution across many local devices.", "Industrial automation; Broadcast; Energy"),
    ("TSN scheduled Ethernet control", "web", "ethernet_wire", ["TSN", "IEEE 802.1Qbv"], "https://1.ieee802.org/tsn/", "Deterministic Ethernet schedules critical control traffic.", "Manufacturing; Automotive; Robotics"),
    ("Edge rules engine", "web", "edge_compute", ["Node-RED", "Rules engine", "HTTPS"], "https://nodered.org/", "Local rules transform PBX/webhook events into device commands.", "SMB; Facilities; Systems integration"),
]


def _expanded_alternatives() -> list[dict]:
    rows = []
    for name, category, medium, protocols, url, use_case, industries in EXPANDED_ALTERNATIVE_SPECS:
        is_web = category == "web"
        latency = "<50ms on LAN, WAN dependent" if is_web else "Sub-ms to seconds, medium dependent"
        reliability = "High with retries and monitoring" if is_web else "Medium-High with engineered installation"
        security = "TLS/mTLS, signed payloads, RBAC, network segmentation" if is_web else "Physical security, link-layer security where supported, gateway authentication"
        cost = "Low-Medium" if is_web else "Low-Medium hardware plus installation"
        rows.append(
            {
                "name": name,
                "category": category,
                "medium": medium,
                "description": f"{name} as an alternative trigger or command path when PSTN line signaling is unavailable, expensive, or too limited.",
                "protocols": protocols,
                "latency": latency,
                "bandwidth": "Small command/event payloads",
                "range": "IP routed" if is_web else "Local, campus, regional, or carrier/radio footprint",
                "reliability": reliability,
                "security": security,
                "complexity": "Medium",
                "cost": cost,
                "use_case": use_case,
                "pros": [
                    "Broadens migration options beyond PSTN and classic PBX lines",
                    "Can be selected by site constraints, latency, and available infrastructure",
                    "Integrates with gateways, edge controllers, or automation middleware",
                ],
                "cons": [
                    "Requires validation against local device support and regulations",
                    "Operational tooling and monitoring differ by protocol",
                    "May need a gateway layer to connect with PBX or UCaaS events",
                ],
                "standards": protocols,
                "resource_url": url,
                "industry_fit_override": industries,
            }
        )
    return rows


def generate_awesome_list(
    output_path: Optional[str] = "data/processed/awesome_list.csv",
) -> pd.DataFrame:
    """Generate the comprehensive PSTN-alternatives awesome list."""
    all_alts = PSTN_ALTERNATIVES_CABLE + PSTN_ALTERNATIVES_WIRELESS + _expanded_alternatives()
    rows = []
    for alt in all_alts:
        rows.append(
            {
                "name": alt["name"],
                "category": alt["category"],
                "medium": alt["medium"],
                "description": alt["description"],
                "protocols": "; ".join(alt["protocols"]),
                "latency": alt["latency"],
                "bandwidth": alt["bandwidth"],
                "range": alt.get("range", "N/A (IP-routed)"),
                "reliability": alt["reliability"],
                "security": alt["security"],
                "complexity": alt["complexity"],
                "cost": alt["cost"],
                "cost_model": _alternative_cost_model(alt),
                "recommended_devices": _alternative_device_range(alt),
                "industry_fit": alt.get("industry_fit_override") or _alternative_industries(alt),
                "use_case": alt["use_case"],
                "pros": "; ".join(alt["pros"]),
                "cons": "; ".join(alt["cons"]),
                "standards": "; ".join(alt["standards"]),
                "resource_url": alt.get("resource_url") or ALT_RESOURCE_URLS.get(alt["name"], ""),
            }
        )
    df = pd.DataFrame(rows)
    if output_path is not None and len(df):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
    return df


def get_awesome_list_json() -> list[dict]:
    """Return the raw awesome list as Python dicts for SPA consumption."""
    return PSTN_ALTERNATIVES_CABLE + PSTN_ALTERNATIVES_WIRELESS + _expanded_alternatives()
