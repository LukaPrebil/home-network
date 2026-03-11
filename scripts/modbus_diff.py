#!/usr/bin/env python3
"""Modbus register diff tool for reverse-engineering Carel pCO heat pump registers.

Usage:
    python scripts/modbus_diff.py --type holding --start 0 --count 100
    python scripts/modbus_diff.py --type input --start 0 --count 100
    python scripts/modbus_diff.py --type coil --start 0 --count 200
    python scripts/modbus_diff.py --type discrete --start 0 --count 200

Workflow:
    1. Takes Snapshot A of the specified register range
    2. Pauses — you go change a setting on the heat pump
    3. Takes Snapshot B of the same range
    4. Prints only the registers that changed
"""

import argparse
import sys
import time

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException

DEFAULT_HOST = "192.168.1.160"
DEFAULT_PORT = 502
DEFAULT_TIMEOUT = 3
DEFAULT_SLAVE_ID = 1
# Carel boards are slow — read in small chunks to avoid dropped packets
CHUNK_SIZE = 10
CHUNK_DELAY = 0.3  # seconds between reads


def read_registers(client, reg_type, start, count, slave_id):
    """Read a block of registers in small chunks, returning {address: value}."""
    results = {}
    for offset in range(0, count, CHUNK_SIZE):
        addr = start + offset
        chunk = min(CHUNK_SIZE, count - offset)

        try:
            if reg_type == "holding":
                resp = client.read_holding_registers(addr, count=chunk, device_id=slave_id)
            elif reg_type == "input":
                resp = client.read_input_registers(addr, count=chunk, device_id=slave_id)
            elif reg_type == "coil":
                resp = client.read_coils(addr, count=chunk, device_id=slave_id)
            elif reg_type == "discrete":
                resp = client.read_discrete_inputs(addr, count=chunk, device_id=slave_id)
            else:
                print(f"Unknown register type: {reg_type}")
                sys.exit(1)

            if resp.isError() or isinstance(resp, ModbusIOException):
                # Unmapped registers — skip silently
                time.sleep(CHUNK_DELAY)
                continue

            if reg_type in ("coil", "discrete"):
                values = resp.bits[:chunk]
            else:
                values = resp.registers

            for i, val in enumerate(values):
                results[addr + i] = val

        except Exception as e:
            print(f"  Warning: error reading {addr}-{addr + chunk - 1}: {e}")

        time.sleep(CHUNK_DELAY)

    return results


def format_address(reg_type, addr):
    """Format address with the conventional Modbus prefix."""
    prefixes = {
        "coil": 0,
        "discrete": 10000,
        "input": 30000,
        "holding": 40000,
    }
    return f"{prefixes[reg_type] + addr}"


def main():
    parser = argparse.ArgumentParser(description="Modbus register diff tool")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Elfin EW11 IP (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Modbus TCP port (default: {DEFAULT_PORT})")
    parser.add_argument("--slave", type=int, default=DEFAULT_SLAVE_ID, help=f"Modbus slave ID (default: {DEFAULT_SLAVE_ID})")
    parser.add_argument("--type", required=True, choices=["holding", "input", "coil", "discrete"], help="Register type to scan")
    parser.add_argument("--start", type=int, default=0, help="Start address (default: 0)")
    parser.add_argument("--count", type=int, default=100, help="Number of registers to read (default: 100)")
    args = parser.parse_args()

    client = ModbusTcpClient(args.host, port=args.port, timeout=DEFAULT_TIMEOUT)

    if not client.connect():
        print(f"Failed to connect to {args.host}:{args.port}")
        sys.exit(1)

    print(f"Connected to {args.host}:{args.port}")
    print(f"Scanning {args.type} registers {args.start} - {args.start + args.count - 1} (slave {args.slave})")
    print()

    # --- Snapshot A ---
    print("Taking Snapshot A...")
    snap_a = read_registers(client, args.type, args.start, args.count, args.slave)
    print(f"  Read {len(snap_a)} registers with values")
    print()

    # --- Human pause ---
    input(
        "Snapshot A taken. Go physically change the target setting on the heat pump screen,\n"
        "wait 5 seconds, then press ENTER here..."
    )
    print()

    # --- Snapshot B ---
    print("Taking Snapshot B...")
    snap_b = read_registers(client, args.type, args.start, args.count, args.slave)
    print(f"  Read {len(snap_b)} registers with values")
    print()

    client.close()

    # --- Diff ---
    all_addrs = sorted(set(snap_a.keys()) | set(snap_b.keys()))
    changes = []
    for addr in all_addrs:
        val_a = snap_a.get(addr)
        val_b = snap_b.get(addr)
        if val_a != val_b:
            changes.append((addr, val_a, val_b))

    if not changes:
        print("No changes detected. Try a larger range or a different register type.")
    else:
        print(f"Found {len(changes)} changed register(s):")
        print()
        print(f"  {'Address':<12} {'Prefixed':<12} {'Old':<10} {'New':<10} {'Note'}")
        print(f"  {'-' * 12} {'-' * 12} {'-' * 10} {'-' * 10} {'-' * 20}")
        for addr, old, new in changes:
            prefixed = format_address(args.type, addr)
            note = ""
            if args.type in ("holding", "input") and old is not None and new is not None:
                # Check if this looks like a Carel-scaled temperature
                if 100 <= old <= 800 or 100 <= new <= 800:
                    note = f"(÷10: {old / 10:.1f} → {new / 10:.1f} °C?)"
            print(f"  {addr:<12} {prefixed:<12} {old!s:<10} {new!s:<10} {note}")


if __name__ == "__main__":
    main()
