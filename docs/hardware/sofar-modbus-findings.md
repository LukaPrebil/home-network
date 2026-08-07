# SOFAR ESI 12K-T1: Modbus transport findings

Empirical results from probing the plant's local interfaces. Written to stop anyone
retrying paths that have already been ruled out.

Probe date: 2026-08-07. Firmware at time of testing: logger stick
`LSW3_15_MQTT_270A_1.22`, inverter `V000001_V000003`.

For the design and register map see
[`sofar-inverter-ha-integration.md`](sofar-inverter-ha-integration.md). For the
decision that followed, see ADR 0008.

## Summary

**The LSW-3 logger stick cannot be polled locally on this firmware.** Neither Modbus
nor Solarman V5 gets a reply. Local telemetry has to come from a wired RS485 bridge on
the inverter's COM port.

## Port scan

Against the stick at `192.168.1.6`:

| Port | Result |
|---|---|
| 8899 | open |
| 80 | open, HTTP 401 on `GET /` |
| 443 | closed |
| 502 | closed |
| 8080 | closed |

ICMP round trip about 9 ms, consistent with Wi-Fi rather than a wired path.

Port 8899 being open is what made the local path look viable. It is not sufficient:
the port accepts connections and serves nothing.

## Protocol probes on 8899

Every attempt below completed the TCP handshake and was never reset by the peer. All
of them then timed out with no reply. That combination, accept and silence rather than
refuse, is the important detail.

| Framing | Unit | Registers tried | Result |
|---|---|---|---|
| Modbus TCP (MBAP header, no CRC) | 1 | 0x0445, 0x0404, 0x0210 | no reply |
| Modbus TCP (MBAP header, no CRC) | 0 | 0x0445 | no reply |
| Modbus RTU over TCP (no header, CRC16) | 1 | 0x0445, 0x0404, 0x0210 | no reply |
| Solarman V5, wrapping Modbus RTU | 1 | 0x0445, 0x0210, 0x0586, 0x0488 | no reply |

All probes used function code 3. Nothing was written at any point.

The V5 frame was verified field by field against `pysolarmanv5`, the reference
implementation, before the negative result was accepted:

| Field | Reference | Probe |
|---|---|---|
| Header | `A5` + `<H` length + `10` + `45` + seq + `<I` logger serial | identical |
| Length | `15 + len(modbus_frame)` | identical |
| Payload | frametype `02`, sensortype, three 4-byte time fields, modbus RTU | identical |
| Checksum | `sum(frame[1:]) & 0xFF` over header and payload | identical |

Only the sequence number differed, which loggers do not validate. The probe was
correct, so the silence is the stick's behaviour and not a malformed request.

## Why the port answers nothing

The stick's hidden config page (`config_hide.html`, HTTP basic auth) reports:

| Setting | Value |
|---|---|
| Working mode | Data collection |
| Internal server protocol | TCP-Server |
| Internal server port | 8899 |
| Internal server address | `10.10.100.254` |
| Serial port | 9600 / 8 / None / 1, CTSRTS disabled |
| Mode select | AP+STA |
| Inverter brand select | Sofar_G3 |

Two things stand out. The internal server is bound to `10.10.100.254`, which is the
stick's access-point-side address, not its LAN address. And the working mode is Data
collection, in which the module's own cloud-polling process owns the RS485 port, so
the transparent TCP server has nothing to bridge.

Published guidance that Data collection mode runs local polling in parallel with the
cloud describes the older SolarMan-protocol firmware. This unit runs MQTT firmware and
reports to SofarCloud, and the local V5 server does not appear to be running.

## Server B is a failover slot, not a second stream

The stick exposes two upstream server slots. Both were configured to
`access3.solarmanpv.com:10000` over TCP, with Server A connected and the optional
server persistently **not** connected.

Tested directly: the optional server was repointed at a LAN address running a
receive-only V5 listener, and saved. Nothing ever connected. Server A stayed up
throughout.

A backup target that will not connect to a working server it already knows is a
standby, not a parallel feed. Repointing it changes nothing while Server A is healthy.

**Do not retry this.** If you want local capture through the upstream path, the only
version that works is redirecting Server **A** to a local relay that forwards to the
real cloud, which means running a proxy service and, because this estate has no MQTT
broker, either standing one up or writing a custom integration.

## Paths ruled out

| Path | Status |
|---|---|
| Raw Modbus TCP on 8899 | Dead. Three framings, no reply |
| Solarman V5 on 8899 | Dead. Frame verified against the reference library |
| `ha-solarman` | Unusable. It needs the V5 server the firmware is not running |
| `homeassistant-solax-modbus` over the stick | Unusable. It speaks only `tcp` and `serial`, with no Solarman V5 support anywhere in its source |
| Server B local capture | Dead. Failover only, tested |
| Server A redirect through a local relay | Technically viable, disproportionate. Needs a proxy service plus a broker this estate does not have |
| Transparency mode on the stick | Works, but disables SofarCloud and allows a single client. Rejected while warranty diagnostics matter |
| Wired RS485 bridge on the inverter COM port | The remaining path. See ADR 0008 |

## Correcting an earlier claim

The transferred research asserted that `homeassistant-solax-modbus` connects "via
LSW-3/LSE-3 on port 8899". Checked against the source: the integration has zero
occurrences of "solarman" or "v5", and its only interfaces are `tcp` and `serial`. The
claim holds only for a stick in Transparency mode, where 8899 serves raw Modbus RTU
over TCP. It is false for a stick in Data collection mode.

That research has now been wrong on the string layout, the firmware versioning scheme,
and this. Treat what remains of it as leads, not facts.
