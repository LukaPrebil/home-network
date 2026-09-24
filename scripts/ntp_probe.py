#!/usr/bin/env python3
"""Measure this host's clock offset against NTP servers without touching the clock.

Each round sends one client packet to every server and appends one CSV row per
valid reply. Offset follows RFC 5905, ((t2 - t1) + (t3 - t4)) / 2, and is
positive when this host is behind the server. Path asymmetry bounds each
sample's error to +/- delay / 2, so analysis should favour low-delay samples.

Usage:
    python3 ntp_probe.py --servers ntp1.arnes.si,ntp2.arnes.si --out samples.csv --duration 86400
    python3 ntp_probe.py --servers ntp1.arnes.si --out - --once
"""
import argparse
import csv
import os
import socket
import struct
import sys
import time

NTP_UNIX_DELTA = 2208988800
PACKET = struct.Struct("!BBbbIII4Q")


def to_ntp(ns):
    sec, rem = divmod(ns, 1_000_000_000)
    return ((sec + NTP_UNIX_DELTA) << 32) | ((rem << 32) // 1_000_000_000)


def from_ntp(ts):
    return ((ts >> 32) - NTP_UNIX_DELTA) * 1_000_000_000 + (((ts & 0xFFFFFFFF) * 1_000_000_000) >> 32)


def short_to_us(value):
    return (value >> 16) * 1e6 + (value & 0xFFFF) * 1e6 / 65536


def query(addr, timeout):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        t1 = time.time_ns()
        xmt = to_ntp(t1)
        sock.sendto(PACKET.pack(0x23, 0, 0, 0, 0, 0, 0, 0, 0, 0, xmt), (addr, 123))
        while True:
            data, _ = sock.recvfrom(512)
            t4 = time.time_ns()
            if len(data) < PACKET.size:
                continue
            fields = PACKET.unpack(data[: PACKET.size])
            if fields[8] == xmt:
                break
    li_vn_mode, stratum, _, _, root_delay, root_disp, refid, _, _, recv, xmit = fields
    if li_vn_mode & 0x7 != 4:
        return None
    refid_text = refid.to_bytes(4, "big").decode("ascii", "replace").strip("\x00") if stratum <= 1 else socket.inet_ntoa(refid.to_bytes(4, "big"))
    if stratum == 0 or li_vn_mode >> 6 == 3:
        return {"kod": refid_text or "UNSYNC"}
    t2, t3 = from_ntp(recv), from_ntp(xmit)
    return {
        "stratum": stratum,
        "refid": refid_text,
        "offset_us": ((t2 - t1) + (t3 - t4)) / 2000,
        "delay_us": ((t4 - t1) - (t3 - t2)) / 1000,
        "root_delay_us": short_to_us(root_delay),
        "root_disp_us": short_to_us(root_disp),
    }


def resolve(name):
    return socket.getaddrinfo(name, 123, socket.AF_INET, socket.SOCK_DGRAM)[0][4][0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--servers", required=True, help="comma-separated host names")
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", default=socket.gethostname())
    parser.add_argument("--interval", type=float, default=64.0)
    parser.add_argument("--duration", type=float, default=86400.0)
    parser.add_argument("--start-delay", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    servers = [(name, resolve(name)) for name in args.servers.split(",")]
    backoff = {name: 0.0 for name, _ in servers}
    new_file = not os.path.exists(args.out)
    out = open(args.out, "a", newline="") if args.out != "-" else sys.stdout
    writer = csv.writer(out)
    if new_file or args.out == "-":
        writer.writerow(["unix_s", "label", "server", "addr", "stratum", "refid", "offset_us", "delay_us", "root_delay_us", "root_disp_us"])

    time.sleep(args.start_delay)
    end = time.monotonic() + args.duration
    while True:
        round_start = time.monotonic()
        for name, addr in servers:
            if backoff[name] > time.monotonic():
                continue
            try:
                reply = query(addr, args.timeout)
            except OSError:
                continue
            if reply is None:
                continue
            if "kod" in reply:
                backoff[name] = time.monotonic() + 16 * args.interval
                writer.writerow([f"{time.time():.3f}", args.label, name, addr, 0, reply["kod"], "", "", "", ""])
                continue
            writer.writerow([
                f"{time.time():.3f}", args.label, name, addr, reply["stratum"], reply["refid"],
                f"{reply['offset_us']:.1f}", f"{reply['delay_us']:.1f}",
                f"{reply['root_delay_us']:.1f}", f"{reply['root_disp_us']:.1f}",
            ])
            time.sleep(0.5)
        out.flush()
        if args.once or time.monotonic() >= end:
            break
        time.sleep(max(0.0, args.interval - (time.monotonic() - round_start)))


if __name__ == "__main__":
    main()
