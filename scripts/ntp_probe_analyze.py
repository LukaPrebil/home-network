#!/usr/bin/env python3
"""Summarise ntp_probe.py CSVs: per-host offset against each reference, and host-to-host differences.

A sample's true error lies within +/- delay / 2 of its offset. Samples whose
delay exceeds the per-(host, server) minimum by more than --delay-margin-us
are dropped, since queueing inflates both delay and asymmetry.
Host differences pair samples to the same server taken within --pair-window-s,
which cancels the shared WAN path asymmetry.

Usage:
    python3 ntp_probe_analyze.py samples-*.csv
"""
import argparse
import csv
import statistics
from collections import defaultdict


def pct(values, q):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))]


def describe(values):
    return (
        f"n={len(values):5d}  median={statistics.median(values):9.1f}  "
        f"p5={pct(values, 0.05):9.1f}  p95={pct(values, 0.95):9.1f}  "
        f"max|x|={max(abs(v) for v in values):9.1f}  sd={statistics.pstdev(values):8.1f}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", nargs="+")
    parser.add_argument("--servers", default="ntp1.arnes.si,ntp2.arnes.si")
    parser.add_argument("--delay-margin-us", type=float, default=1000.0)
    parser.add_argument("--pair-window-s", type=float, default=40.0)
    args = parser.parse_args()
    wanted = set(args.servers.split(","))

    rows = []
    for path in args.csv:
        with open(path, newline="") as handle:
            for row in csv.DictReader(handle):
                if row["offset_us"] and row["server"] in wanted:
                    rows.append((float(row["unix_s"]), row["label"], row["server"], float(row["offset_us"]), float(row["delay_us"])))

    min_delay = defaultdict(lambda: float("inf"))
    for _, label, server, _, delay in rows:
        min_delay[label, server] = min(min_delay[label, server], delay)
    kept = [r for r in rows if r[4] <= min_delay[r[1], r[2]] + args.delay_margin_us]

    span = (max(r[0] for r in kept) - min(r[0] for r in kept)) / 3600 if kept else 0
    print(f"samples kept {len(kept)} of {len(rows)}, span {span:.1f} h, servers {sorted(wanted)}")
    print("\nOffset of reference minus host clock, us (positive = host behind)")
    by_host = defaultdict(list)
    for _, label, server, offset, _ in kept:
        by_host[label].append(offset)
    for label in sorted(by_host):
        print(f"  {label:11s} {describe(by_host[label])}")
    print("\nMinimum delay per host/server, us (error bound per sample is half of this or more)")
    for (label, server), delay in sorted(min_delay.items()):
        print(f"  {label:11s} {server:16s} {delay:8.0f}")

    series = defaultdict(list)
    for ts, label, server, offset, _ in kept:
        series[label, server].append((ts, offset))
    labels = sorted(by_host)
    print("\nHost A clock minus host B clock, us, paired on the same server")
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            diffs = []
            for server in wanted:
                other = series.get((b, server), [])
                for ts, offset_a in series.get((a, server), []):
                    near = [o for t, o in other if abs(t - ts) <= args.pair_window_s]
                    if near:
                        diffs.append(near[0] - offset_a)
            if diffs:
                print(f"  {a} - {b}: {describe(diffs)}")

    print("\nHourly median offset, us")
    hourly = defaultdict(lambda: defaultdict(list))
    for ts, label, _, offset, _ in kept:
        hourly[int(ts // 3600)][label].append(offset)
    print("  hour(UTC)  " + "".join(f"{label:>12s}" for label in labels))
    for hour in sorted(hourly):
        cells = "".join(
            f"{statistics.median(hourly[hour][label]):12.0f}" if hourly[hour][label] else f"{'-':>12s}" for label in labels
        )
        print(f"  {hour % 24:02d}:00      {cells}")


if __name__ == "__main__":
    main()
