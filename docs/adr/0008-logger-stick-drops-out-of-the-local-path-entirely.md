# The logger stick drops out of the local path entirely

Status: accepted (2026-08-07)

Supersedes the monitoring half of ADR 0007. Its control decision stands unchanged.

ADR 0007 split the plant's local access in two: monitoring over the LSW-3 Wi-Fi logger
stick, control over a wired RS485 bridge, on the grounds that reads degrade honestly
over a lossy transport while writes degrade silently. That reasoning survives. The
arrangement does not, because the premise underneath it was false. The stick does not
serve local polling at all on firmware `LSW3_15_MQTT_270A_1.22`. Port 8899 is open and
accepts connections, which is what made the path look viable, but it answers neither
raw Modbus TCP, nor Modbus RTU over TCP, nor Solarman V5 addressed with the correct
logger serial. Connections are accepted and never reset, then time out in silence. The
V5 probe was verified field by field against `pysolarmanv5` before the negative was
believed, so the fault is not in the request. The stick's own config page explains it:
the working mode is Data collection, in which the module's cloud-polling process owns
the RS485 port, and the internal TCP server is bound to `10.10.100.254`, the
access-point-side address rather than the LAN one. Published guidance describing
parallel local access in Data collection mode belongs to the older SolarMan-protocol
firmware, not to this MQTT build reporting to SofarCloud. **We therefore stop treating
the stick as part of the local path.** It keeps doing exactly one job, pushing to
SofarCloud for warranty diagnostics, and every byte Home Assistant reads will come from
a wired Elfin EE11A on the inverter's COM port. Local telemetry does not begin until
that hardware lands, which is roughly a month out. Full evidence in
[`sofar-modbus-findings.md`](../hardware/sofar-modbus-findings.md).

## Considered options

- **Transparency mode on the stick** - rejected: it does serve raw Modbus RTU over TCP
  and would work immediately, but it disables SofarCloud and permits one TCP client.
  ADR 0007 already weighed and rejected that trade while the plant is new and warranty
  diagnostics are the only remaining recourse, and nothing about the situation has made
  the trade better. It also puts battery-facing traffic back on Wi-Fi.
- **`ha-solarman` instead of `homeassistant-solax-modbus`** - rejected: it speaks
  Solarman V5, which is precisely the protocol the stick refuses to answer. This was
  the fallback ADR 0007 held in reserve, and it is unusable for the same reason as
  everything else on 8899.
- **Local capture through the stick's second upstream server** - rejected: tested
  directly by repointing the optional server at a receive-only listener on the LAN. It
  never connected, while Server A stayed up throughout. The slot is a failover standby,
  not a parallel feed.
- **Redirect the primary upstream server through a local relay** - rejected as
  disproportionate: technically sound, and it would preserve the cloud by forwarding
  onward while capturing every pushed frame. It needs a proxy service, a frame parser,
  and a route into Home Assistant, which this estate cannot provide without standing up
  an MQTT broker it deliberately removed in June 2026. That is a large build to bridge
  a one-month hardware wait.
- **Accept cloud-only telemetry until the bridge arrives** - accepted, by elimination.
  It costs roughly a month of unrecoverable local history and nothing else.

## Consequences

- Phase 1 no longer exists as a separate step. There is no cheap interim integration to
  stand up first, so the first working Home Assistant integration is the wired one, and
  the phased plan collapses from three stages to two.
- The EE11A moves onto the critical path for all local data, not just for control. Two
  were ordered on 2026-08-07, one for the inverter COM port and one for the TIGO CCA
  optimizer tap, so the two month-long lead times run concurrently instead of in
  sequence.
- The **A** variant is required, not incidental. The plain EE11 accepts 5-18 VDC and the
  enclosure supplies 24 V; only the EE11A spans 5-36 VDC. The same reasoning already
  applies to the EW11A on the heat pump.
- Roughly a month of production history exists only in SofarCloud, at whatever
  retention and granularity that portal chooses. It cannot be backfilled locally.
- `homeassistant-solax-modbus` remains the integration, and the `SH1` serial prefix is
  still handled upstream, so the install stays stock. Only its transport changed, and
  it will be configured against the bridge from the first connection rather than being
  migrated onto it later. The entity-churn problem that shaped ADR 0007's integration
  choice disappears, because there is now only ever one transport.
- Phase 3, optimizer telemetry via `taptap-mqtt`, assumes an MQTT broker this estate
  does not have. That gap is now explicit and has to be resolved before the TIGO tap
  produces anything, whether by standing up a broker or by choosing a different path
  into Home Assistant.
- The stick keeps its static DHCP lease and its cloud connection, and is otherwise
  inert from the automation side. Anyone finding port 8899 open on it in future should
  read the findings document before spending an evening on it.
