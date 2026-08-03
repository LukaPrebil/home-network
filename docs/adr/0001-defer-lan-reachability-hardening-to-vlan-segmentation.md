# Defer flat-LAN reachability hardening to VLAN segmentation

Status: accepted (2026-06-10)

The 2026-06-10 security review found a family of findings with a single shared root cause: every host sits on one flat subnet alongside IoT and guest devices. Storage, home-automation transports, and service backends are therefore reachable from any device on the LAN rather than from a scoped set of peers, and no finding in the family can be fixed properly without changing that.

We decided NOT to apply interim per-IP mitigations and instead accept these exposures until the VLAN segmentation already designed in `docs/network-architecture.md` is implemented. Rationale: per-IP allowlists on a flat L2 are defeated by IP spoofing anyway, they add churn that the VLAN migration would immediately rewrite, and tightening service bindings breaks legitimate consumers that reach those services over the LAN by design.

Consequences: until the VLAN migration lands, any device on the LAN is inside the trust boundary, and the WAN edge (Cloudflare -> Traefik -> CrowdSec) is the only enforced perimeter. Impact-reduction hardening that is independent of reachability (secret file modes, docker-socket scoping, disabling unused admin APIs, fail-fast on missing auth config) is explicitly NOT deferred. Every finding deferred here is re-scoped as work inside the VLAN migration, which is not done until each one has been revisited against the segmented topology.
