# TIGO optimizer telemetry runs over MQTT, using the add-on image with its entrypoint bypassed

Status: accepted (2026-08-26).

The tap bridge on the TIGO CCA is live and `taptap observe` decodes it cleanly, so the
question was no longer whether per-panel telemetry is possible but which of four routes
carries it into Home Assistant. We chose `taptap-mqtt` behind a new Mosquitto broker on
the containers VM, and we run the maintainer's Home Assistant add-on image as an
ordinary container with its entrypoint overridden, rendering `config.ini` from an
Ansible template instead of from the add-on's own init script.

Three parts of that will look wrong to a future reader, so each is recorded here.

## Considered options

- **PyTap** (`azebro/pytap`), a HACS integration that connects straight to the tap
  bridge over TCP - rejected despite being the obvious choice on architecture. It is one
  moving piece against three, needs no broker, no bridge process and no `taptap` binary,
  and its vendored protocol parser carries unit tests. It was rejected on maturity: two
  open issues, unfixed since May and June 2026, describe panel values freezing at their
  last daytime reading overnight rather than zeroing. That corrupts daily energy totals
  and any dead-optimizer logic built on top, and it fails invisibly - a frozen value at
  22:00 looks entirely plausible. A third open issue covers exactly the recorder
  write-volume problem this plant would hit at 30 panels. No release since June 2026,
  five stars, one maintainer. `taptap-mqtt` has 22 releases across 13 months and has
  already found and fixed the same classes of bug against other people's arrays: node
  availability, timezone parsing, energy integration, and per-model power miscalculation.
  We would rather carry three pieces that other plants have debugged than one piece that
  they have not.
- **`mletenay/home-assistant-tigo`** - rejected on warranty grounds, though it is the
  most-starred option. It talks to the CCA's local web console rather than the RS485
  bus, and reaching that console requires rooting the CCA: SSH in, remount the
  filesystem writable, rewrite network rules. Its own README warns this may void the
  warranty and can brick the device. ADR 0007 and ADR 0008 both preserved a cloud uplink
  specifically to keep a warranty-diagnosis channel open after the handover record was
  signed; rooting the gateway spends more of that than either rejected option did.
- **`Bobsilvio/tigosolar-online`** - rejected: it works today with no hardware at all,
  via TIGO's official cloud API, which puts the cloud back into the path this whole
  effort exists to remove.
- **Running the add-on properly, as an add-on on HAOS** - rejected. It is the supported
  path and it is genuinely cheaper. But HAOS is not Ansible-managed in this estate: it
  has no SSH, `provision-haos.yml` is a one-shot provisioner with interactive steps, and
  nothing converges it. The cost of that is already visible in this repo, where
  `provision-haos.yml` still pointed MQTT at rpi4 two months after that broker was
  deleted. Putting a broker back on HAOS would re-enter precisely the trap that produced
  that stale line.
- **Building our own bridge image** from the single `taptap-mqtt.py`, its three pip
  dependencies and the `taptap` release tarball - rejected as the fallback rather than
  the default. It removes all reliance on add-on internals, but this repo has no
  image-build or distribution pattern; every other role consumes an upstream image.
  Reconsider if the paths inside the add-on image ever move.
- **Native binary plus systemd**, following the AdGuard-on-rpi4 precedent - rejected:
  viable, but it trades a pinned upstream image for install and upgrade logic we would
  own, on a host where every other service is a container.

## Consequences

- **The add-on image cannot self-configure outside HAOS, and this is not obvious.** Its
  init script builds `config.ini` through `bashio::config`, and in bashio v0.17.5 - the
  version baked into this image - that resolves to
  `bashio::api.supervisor GET /addons/self/options/config`. It calls the Supervisor API,
  not `/data/options.json`. Older bashio read the file, which is why the usual trick of
  mounting a hand-written `options.json` does not work here. Left alone, every config
  lookup errors, `config.ini` never renders and s6 halts the container. We therefore
  bypass s6 and bashio entirely and invoke `taptap-mqtt.py` directly against a templated
  `config.ini`. The `config.ini` format is upstream and documented, so the contract we
  depend on is stable; the only image-internal assumption is two file paths, and a
  version bump that moved them would fail loudly at container start.
- **A broker exists again, two months after one was deliberately removed.** The orphaned
  MQTT integration was deleted on 2026-06-04 because nothing consumed it. This broker has
  exactly one real consumer. The "several consumers justify a broker" argument was
  checked and does not hold: `Sofar2mqtt` is superseded by the `solax-modbus` decision in
  ADR 0007 and 0008, the Eufy L60 is explicitly not an MQTT device, and `fan2mqtt` is a
  commercial licence for HRV hardware that has not been bought. It is nonetheless
  declared as a shared contract in `group_vars/all/main.yml` rather than as role-local
  configuration, so a second consumer costs a credential rather than a refactor.
- **The module mapping is a hard prerequisite, not a later refinement.** Serials are
  optional in the bridge's config, but omitting one makes it assign discovered modules to
  randomly picked names. The failure mode is confidently mislabelled data, not missing
  data, and it cannot be repaired retroactively because everything recorded before the
  fix is attributed to the wrong panel. Nothing on the bus carries panel position: node
  IDs are gateway-assigned and unstable, serial frames appear rarely and mostly at night,
  and gateway membership is not string membership. All 30 serials come from TIGO EI
  before first deploy.
- **Panel labels are provisional for roughly the first day, and that was accepted
  deliberately.** Configuring the serials is necessary but not sufficient: the map the
  operator supplies is position to serial, while the telemetry on the wire carries only a
  gateway-assigned node ID. The missing serial-to-node-ID link arrives only in
  enumeration frames, which are rare and mostly nocturnal - a 60 second capture on this
  plant produced 68 power reports and zero barcode frames. Until one arrives per node,
  the bridge assigns each node the first unused name in the list, so every panel reports
  real values under a guessed label.

  **Correction, 2026-08-27.** This bullet originally claimed the guess self-corrects on
  the first barcode frame. It does not, and the failure is silent. taptap did learn the
  full topology overnight and persisted it at 06:38, but the bridge left all 30 panels on
  their guessed names for hours afterwards: when an infrastructure report arrives *after*
  temporary mappings already exist, the bridge does not reconcile them. Nothing is logged
  and nothing raised. The obvious health signal actively misleads - `nodes_identified_count`
  read 30 throughout, because it counts nodes holding any node ID, guessed or confirmed.
  The only true signal is the count of `Permanently enumerated` lines, which sat at 0.

  Ordering is the whole problem, so a restart is the whole fix: with the state file
  already on disk, taptap emits the infrastructure report before any power report and all
  30 bind immediately. Since taptap persists what it learns, this can only bite a run that
  begins with no state file - a first deploy, or a lost volume. The `taptap_mqtt` role now
  detects exactly that (topology present, bindings incomplete) and restarts once, rather
  than failing loudly and handing the operator the same restart to perform by hand.

  `NODES_AVAILABILITY_IDENTIFIED` would hide per-panel entities until their serial is
  confirmed and avoid the mislabelled window entirely. It is left `false`: the operator
  chose live data from the first day over a clean per-panel history. The cost is that
  per-panel history for the deploy day is attributed to the wrong panels and stays that
  way. String and plant aggregates are unaffected throughout, since a sum over all 30
  modules is identical whichever label each carries.
- **The CCA keeps its internet connection**, reversing the "blocked from the internet"
  line in the Stage 2 plan. That line predated the discovery that TIGO EI is the only
  source of the panel-to-serial mapping. The portal stays the day-one cross-check for
  decoded values, the reference if an optimizer is ever replaced, and the
  warranty-diagnosis channel - the same reasoning that kept SofarCloud alive in ADR 0007
  and 0008. The tap is passive and read-only, so the CCA cannot tell it is there.
- **The bridge is a blind source by construction, and it takes two checks, not one, to
  see it.** If the tap bridge or the CCA goes quiet, the process keeps running and holds
  its MQTT connection open, so its last-will never fires and a container-running probe
  stays green - the fifth instance of a failure shape this estate has already hit four
  times. The repo's convention for a service with no HTTP endpoint would therefore have
  been blind here. The two checks cover different halves and neither covers both:
  - **Process liveness** is the heartbeat file, asserted fresh after deploy and watched
    by a Docker healthcheck so autoheal can restart a wedged bridge. Note the limit: the
    bridge touches that file on every pass of a one-second loop whether or not the bus
    produced anything, so it proves the loop is turning and nothing more.
  - **Data liveness** is Home Assistant entity availability. With
    `NODES_AVAILABILITY_ONLINE` on and a 180 second timeout, the module entities go
    unavailable three minutes after the bus falls silent. This, not the heartbeat, is
    what surfaces a dead tap bridge.

  `MAX_ERROR` is also set non-zero, against the add-on's default of unlimited retries, so
  a bridge failing repeatedly exits and lets the restart policy act instead of retrying
  invisibly forever.
- **Roughly 300 new entities land in a recorder database already at 1.9 GB**, at a 10
  second update interval with long-term statistics on power as well as energy. Disk is
  not the constraint. If SQLite responsiveness degrades, the update interval is a single
  role variable and raising it costs nothing already collected.
