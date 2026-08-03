# Presence Simulation

Simulates occupancy by replaying recorded device history during extended absences.

## Integration

Uses the `slashback100/presence_simulation` HACS integration (v5.1). It replays entity state history from 7 days ago with an optional random timing offset, so the simulation follows actual past behaviour rather than a fixed schedule.

**Entity**: `switch.presence_simulation` - turn on/off to start/stop the simulation.

## Control Automation

**Entity**: `automation.presence_simulation_control`

An automation starts the simulation during a sustained absence and stops it once the house is occupied again. The trigger thresholds and the person entities they watch are configured in Home Assistant and intentionally not documented here.

## Simulated Entities

A small set of interior lights and blinds is registered with the integration. The exact entity list is configured in Home Assistant and intentionally not documented here.

## Setup

After the HACS install, Home Assistant needs a restart. Then configure the integration via Settings > Integrations > Presence Simulation and add the entities that should be replayed.
