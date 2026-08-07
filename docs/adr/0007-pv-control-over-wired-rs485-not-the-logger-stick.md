# PV battery control runs over wired RS485, not the logger stick

Status: accepted (2026-08-07)

The SOFAR ESI 12K-T1 is reachable today on the LSW-3 Wi-Fi logger stick at
`192.168.1.6`, with port 8899 confirmed open even on the newer MQTT-based firmware
`LSW3_15_MQTT_270A_1.22` that accompanied the move from SolarMan to SofarCloud. That
makes the cheap path genuinely live rather than theoretical, so this is a real choice
and not a forced one. We nonetheless split it: **monitoring runs over the stick,
battery control never will.** The reason is not link reliability, which would be the
obvious assumption in a house whose standing rule is that critical automations do not
depend on Wi-Fi. It is write observability. In the stick's default Data Collection
mode, write requests return non-standard response codes, so a write appears to fail
even when it succeeded, and the published workaround is `continue_on_error: true`,
which suppresses the symptom rather than fixing it. Reads degrade honestly under this
transport, since a dropped poll costs one sample in a graph. Writes degrade silently,
and a Passive Mode write that sets the battery's grid target and charge limits is
exactly the class of operation where silent failure is worse than loud failure: the
battery does the wrong thing at the wrong hour of a winter evening and nothing
signals it. Control therefore moves to an Elfin EE11 on the inverter's COM port,
which speaks native Modbus TCP and gives honest function code `0x10` semantics on a
wired path.

## Considered options

- **Control over the logger stick in Data Collection mode** - rejected: keeps the
  cloud portal alive and costs nothing, but leaves every Passive Mode write
  unverifiable. The control loop cannot distinguish its own successes from its own
  failures, which makes any safety reasoning about battery scheduling unsound.
- **Control over the logger stick in Transparency mode** - rejected: gives honest
  write semantics, but disables the cloud portal and permits a single TCP client. With
  the handover record signed and the final payment released, SofarCloud is the channel
  through which the installer would remote-diagnose a warranty claim. Trading a
  warranty affordance for an automation affordance is the wrong trade while the
  system is new. A TCP multiplexer addresses the single-client limit but not the loss
  of cloud.
- **Elfin EW11 rather than EE11** - rejected: the EW11 is the Wi-Fi variant. It would
  have solved the observability problem, since native Modbus over any transport
  reports honestly, and the EW11 already in service on the heat pump has proven
  reliable. It was rejected because the PV enclosure already contains a network switch
  fed by the pre-run hardwired cable, plus the DIN rail and 24V supply the bridge
  needs. Choosing a wireless bridge with an Ethernet port inside the same cabinet
  spends a standing requirement for nothing.
- **Start on `ha-solarman`, migrate to `homeassistant-solax-modbus` later** -
  rejected: `ha-solarman` needs no code edits and would enumerate sooner, but the two
  integrations produce different entity IDs. Switching later costs either the
  accumulated history or entity ID surgery across every dashboard and automation grown
  on top of it. `solax-modbus` connects over the stick on 8899 as well, so starting
  there makes the wired path a host and port change rather than a migration. Retained
  as the fallback if the serial-prefix patch proves intractable, on the grounds that a
  future migration beats accumulating no local history at all.

## Consequences

- One integration spans both phases. `homeassistant-solax-modbus` goes in now against
  the stick with writes unused, and the EE11 later changes only its host and port.
  Entity IDs, history, dashboards, and automations survive the transport swap
  untouched.
- Battery control is gated on hardware arriving. Until the EE11 is wired, the plant is
  observable but not steerable from Home Assistant, and the inverter runs its own Self
  Use mode. Local production history starts accumulating immediately, which is the
  part that cannot be backfilled.
- Wi-Fi appears in the monitoring path of a house that bans it for critical
  automations. This is a conscious exception, not an oversight, and it is bounded to
  reads. A future reader who observes that monitoring works fine over Wi-Fi and
  concludes control can follow the same route would be drawing exactly the wrong
  inference from the evidence.
- SofarCloud stays connected. Nothing automated may depend on it, but it remains the
  remote-diagnosis channel for warranty work, which is now the only channel left since
  the payment leverage is spent.
- `plugin_sofar.py` carries a local patch adding the inverter's serial prefix with
  `HYBRID | X3 | GEN` flags. HACS overwrites it on every integration update until the
  prefix is upstreamed, so upstreaming it is maintenance work, not politeness.
- The EE11's DC input rating needs checking against the enclosure's 24V Delta supply
  before it is connected, since these serial servers are commonly specified for a
  lower range. This is the one open hardware question the decision leaves behind.
