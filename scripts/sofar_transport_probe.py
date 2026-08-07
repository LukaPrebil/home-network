#!/usr/bin/env python3
"""Read-only transport probe for the SOFAR ESI 12K-T1 inverter.

Answers one question: does this endpoint speak anything we can poll? It tries every
framing a Home Assistant integration might use and reports which, if any, replies.

- Modbus TCP (MBAP header, no CRC)      what homeassistant-solax-modbus sends
- Modbus RTU over TCP (no header, CRC16) what a logger stick in Transparency mode wants
- Solarman V5 wrapping Modbus RTU        what ha-solarman sends, needs --serial

Every request uses function code 3 (read holding registers). Nothing is ever written,
so this is safe to run against a live plant.

Use it for:

- Verifying a new RS485 bridge answers before configuring anything in Home Assistant
- Re-testing the logger stick after a firmware change (as of LSW3_15_MQTT_270A_1.22 it
  answers nothing; see docs/hardware/sofar-modbus-findings.md)

Usage:
    python3 scripts/sofar_transport_probe.py <host> [--port 8899] [--serial N]

    # the logger stick, including the V5 attempt
    python3 scripts/sofar_transport_probe.py 192.168.1.6 --serial 1234567890

    # a wired Elfin bridge, which speaks plain Modbus TCP on 502
    python3 scripts/sofar_transport_probe.py 192.168.1.x --port 502

A reply to any framing prints the raw hex plus the decoded register value. Silence on
all of them means the endpoint accepts TCP but serves no pollable protocol.
"""

import argparse
import socket
import struct
import sys

# 0x0445 is where plugin_sofar reads the inverter serial; the rest are live values.
DEFAULT_REGISTERS = [
    (0x0445, "serial block start"),
    (0x0404, "operating status"),
    (0x0210, "battery SOC"),
    (0x0586, "PV1 power"),
    (0x0488, "grid total power"),
]


def crc16(data):
    """Modbus RTU CRC16, low byte first on the wire."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def modbus_rtu_read(slave, addr, count):
    pdu = struct.pack(">BBHH", slave, 3, addr, count)
    return pdu + struct.pack("<H", crc16(pdu))


def frame_modbus_tcp(unit, addr, count):
    pdu = struct.pack(">BHH", 3, addr, count)
    mbap = struct.pack(">HHHB", 1, 0, len(pdu) + 1, unit)
    return mbap + pdu


def frame_v5(logger_serial, unit, addr, count):
    """Wrap a Modbus RTU frame in a Solarman V5 request.

    Field layout matches pysolarmanv5. The sequence number is left at zero because
    loggers do not validate it.
    """
    inner = (
        b"\x02"                                  # frame type
        + b"\x00\x00"                            # sensor type
        + b"\x00" * 12                           # total working / power on / offset time
        + modbus_rtu_read(unit, addr, count)
    )
    head = (
        b"\xa5"
        + struct.pack("<H", len(inner))
        + struct.pack("<H", 0x4510)              # control code, request
        + b"\x00\x00"                            # sequence number
        + struct.pack("<I", logger_serial)
    )
    body = head + inner
    return body + bytes([sum(body[1:]) & 0xFF]) + b"\x15"


def decode_modbus_reply(pdu):
    """Return a human summary of a Modbus RTU/TCP response body, or None."""
    if len(pdu) < 3:
        return None
    if pdu[1] & 0x80:
        return f"EXCEPTION code {pdu[2]}"
    if pdu[1] != 3:
        return None
    nbytes = pdu[2]
    regs = pdu[3 : 3 + nbytes]
    if not regs:
        return None
    return f"{nbytes} data bytes, raw value {int.from_bytes(regs, 'big')}"


def attempt(host, port, timeout, frame, label):
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.settimeout(timeout)
        sock.sendall(frame)
        data = sock.recv(1024)
        sock.close()
    except socket.timeout:
        print(f"  {label}: TIMEOUT (connected, no reply)")
        return
    except OSError as exc:
        print(f"  {label}: {type(exc).__name__}: {exc}")
        return

    if not data:
        print(f"  {label}: connected, peer closed without replying")
        return

    print(f"  {label}: {len(data)} bytes -> {data[:64].hex()}")
    # A V5 response carries the Modbus reply at offset 25 through len-2.
    body = data[25:-2] if data[0] == 0xA5 and len(data) > 27 else data[6:] if len(data) > 8 else data
    summary = decode_modbus_reply(body)
    if summary:
        print(f"      decoded: {summary}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("host", help="IP of the logger stick or RS485 bridge")
    parser.add_argument("--port", type=int, default=8899, help="default 8899 (stick); use 502 for a bridge")
    parser.add_argument("--serial", type=int, help="logger serial, enables the Solarman V5 attempt")
    parser.add_argument("--unit", type=int, default=1, help="Modbus slave id, default 1")
    parser.add_argument("--timeout", type=float, default=4.0, help="per-attempt seconds, default 4")
    args = parser.parse_args()

    print(f"Probing {args.host}:{args.port}, read-only, function code 3\n")

    print("Modbus TCP framing (MBAP header):")
    for addr, label in DEFAULT_REGISTERS:
        attempt(
            args.host, args.port, args.timeout,
            frame_modbus_tcp(args.unit, addr, 1),
            f"0x{addr:04X} {label}",
        )

    print("\nModbus RTU over TCP framing (CRC16):")
    for addr, label in DEFAULT_REGISTERS:
        attempt(
            args.host, args.port, args.timeout,
            modbus_rtu_read(args.unit, addr, 1),
            f"0x{addr:04X} {label}",
        )

    if args.serial is None:
        print("\nSolarman V5: skipped, pass --serial <logger serial> to include it")
        return 0

    print("\nSolarman V5 framing:")
    for addr, label in DEFAULT_REGISTERS:
        attempt(
            args.host, args.port, args.timeout,
            frame_v5(args.serial, args.unit, addr, 1),
            f"0x{addr:04X} {label}",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
