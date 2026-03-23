# Research: Decentralized HRV Units for Residential Use

**Date:** 2026-03-22
**Context:** 150 m2 house in Slovenia. Need 10 units total: 7 standard HRV + 3 bathroom extract. 5 synchronized pairs. Target airflow: ~190 m3/h normal, ~300 m3/h boost.

---

## Summary

Six brands were researched in depth. The comparison focuses on push-pull wall-mounted units that work in synchronized pairs, plus bathroom extract options.

**Key finding:** Blauberg Vento Expert offers the best combination of price, local smart home integration (Modbus over UDP, no cloud), and adequate performance for this project. Lunos is the premium choice with superior acoustics but costs 3x more and requires hardware hacking for HA integration. InVENTer falls in between with solid German engineering but weak smart home support. Prana is budget-friendly with an official HA integration (2026.2) but has questionable build quality long-term.

---

## Brand Comparison

### 1. Blauberg Vento Expert A50-1

**Origin:** Germany (Blauberg Ventilatoren GmbH), Ukrainian parent company
**Slovenian distributor:** [blauberg.si](https://www.blauberg.si/)

#### Models

| Model | Type | WiFi | Humidity Sensor | Use Case |
|---|---|---|---|---|
| A50-1 Pro | Push-pull HRV | No | No | Standard rooms |
| A50-1 W V.3 | Push-pull HRV | Yes | Yes | Standard rooms, smart control |
| A50-1 S10 Pro | Push-pull HRV (shorter tube) | No | No | Thinner walls |
| A50-1 S10 W V.2 | Push-pull HRV (shorter tube) | Yes | Yes | Thinner walls, smart control |
| DUO A30-1 W | Dual-fan single unit | Yes | Yes | Standalone (no pairing needed) |

**Note:** No dedicated bathroom extract model. The W variants with humidity sensor can boost automatically in humid rooms, but there is no IP-rated bathroom-specific unit. For bathrooms, use the W variant with humidity boost or a separate extract fan.

#### Specifications (A50-1 Pro / W)

| Parameter | Speed 1 | Speed 2 | Speed 3 |
|---|---|---|---|
| Airflow (ventilation mode) | 15 m3/h | 30 m3/h | 50 m3/h |
| Airflow (heat recovery mode) | 8 m3/h | 15 m3/h | 25 m3/h |
| Sound pressure at 3 m | 11 dB(A) | 18 dB(A) | 21 dB(A) |
| Sound pressure at 1 m | 20 dB(A) | 27 dB(A) | 30 dB(A) |
| Power consumption | 3.6 W | ~4.5 W | 5.2 W |

- **Heat recovery efficiency:** up to 93% (ceramic enthalpy heat exchanger)
- **SPI:** 0.138 W/(m3/h)
- **Operating temperature:** -20 to +40 C
- **Filter:** G3 standard, optional F7 pollen filter
- **Wall opening:** 160 mm diameter
- **Cycle time:** ~70 seconds per direction

#### Airflow Calculation for This House

With 5 pairs (10 units) at speed 2 in ventilation mode: 10 x 30 = **300 m3/h**
At speed 2 in heat recovery mode: 10 x 15 = **150 m3/h**
At speed 3 in heat recovery mode: 10 x 25 = **250 m3/h**

**Verdict:** Meets the 190 m3/h normal target at speed 2-3 in heat recovery mode. Meets 300 m3/h boost in ventilation mode at speed 2.

#### Pricing

| Source | Model | Price (EUR incl. VAT) |
|---|---|---|
| skybad.de (Germany) | A50-1 Pro (no WiFi) | ~400 |
| heiz24.de (Germany) | A50-1 S10 W V.2 complete set (WiFi) | ~590 |
| Various DE retailers | A50-1 W V.2/V.3 (WiFi) | 480-590 |
| eBay DE | A50-1 Pro V2 | ~830 (overpriced) |

**Estimated total for 10 WiFi units:** ~5,000-5,900 EUR
**Estimated total for 10 Pro units (no WiFi):** ~4,000 EUR

#### Home Assistant Integration - EXCELLENT

This is the standout feature of Blauberg. Multiple integration paths exist:

1. **Local Modbus over UDP (port 4000)** - WiFi units expose a local MODBUS/UDP interface. No cloud required. Protocol is documented.
2. **Custom HA integrations:**
   - [ecovent_v2](https://github.com/gody01/ecovent_v2) - HACS integration for Vento Expert A50/80/100
   - [hass-ecovent](https://github.com/49jan/hass-ecovent) - Custom component
   - [home_assistant_ecovent](https://github.com/aglehmann/home_assistant_ecovent) - Tested with A50-1 W
   - [blauberg-homeassistant](https://github.com/gracingpro/blauberg-homeassistant) - Docker-based Modbus S21 controller integration
3. **MQTT bridge available** - Commercial license from [blomkvistitk.no](https://blomkvistitk.no/produkt/fan2mqtt-mqtt2fan-licenses/?lang=en) for MQTT control
4. **WiFi synchronization** - Units sync via WiFi for coordinated push/pull operation
5. **Auto-discovery** - UDP broadcast discovery on local network

**Compatible brands using same protocol:** EcoVent, Oxxify, TwinFresh (Vents), Duka, Flexit

#### Reliability

- Manufacturer claims frost-free and condensation-free operation
- Slovenian forum user reported good initial results with 4 units in a 135 m2 row house
- Ceramic heat exchanger is robust and cleanable
- IP24 rated

#### Controller

- WiFi units: controlled via Android/iOS app
- Multi-unit synchronization via WiFi (master/slave)
- No dedicated wall controller needed - each unit has touch buttons on indoor panel
- Central control via HA is the best approach

---

### 2. Lunos (e2, e2 60, ego, Silvento)

**Origin:** Germany (Lunos Lueftungstechnik GmbH, Berlin)
**Premium positioning** - widely considered the gold standard for decentralized HRV

#### Models

| Model | Type | Airflow | Use Case |
|---|---|---|---|
| e2 | Push-pull HRV (paired) | 15-38 m3/h per unit | Standard rooms |
| e2 60 | Push-pull HRV (paired, higher flow) | 5-60 m3/h per unit | Larger rooms |
| ego | Dual-fan single unit (standalone) | Up to 20 m3/h HRV, 45 m3/h extract | Bathrooms, kitchens |
| Nexxt E | Counter-flow HRV (continuous, standalone) | Up to 100+ m3/h | Large rooms |
| Silvento ec | Extract-only fan | 15-60 m3/h (up to 100 m3/h) | Bathrooms, WC |

#### Specifications

**e2 (standard):**

| Parameter | Level 1 | Level 2 | Level 3 |
|---|---|---|---|
| Airflow | ~15 m3/h | ~31 m3/h | ~38 m3/h |
| Sound (at distance) | 16.5 dB(A) | ~22 dB(A) | ~26 dB(A) |
| Power consumption | 0.7 W | ~2.5 W | 4 W |

- Heat recovery: up to 96% (85% per EN 13141-8)
- SPI: 0.09 W/(m3/h) - best in class
- Supply voltage: 12V DC SELV
- Min wall thickness: 300 mm
- Diameter: 154 mm

**e2 60 (higher flow):**

| Parameter | Level 1 | Level 2 | Level 3 |
|---|---|---|---|
| Airflow | 17 m3/h | 32 m3/h | 38 m3/h (up to 60 m3/h) |
| Sound at 3 m | 3-16 dB(A) | 19.5 dB(A) | 26 dB(A) (up to 39 dB(A)) |
| Power consumption | 0.4 W | ~2 W | 3.3 W |

- Heat recovery: 96% at 20 m3/h, 90% at 40 m3/h, 85% at 60 m3/h
- Sound insulation: up to 67 dB - best in class

**ego (bathroom/kitchen):**
- Airflow: up to 20 m3/h (HRV mode), 45 m3/h (extract mode)
- Heat recovery: 81.4%
- Sound: 16.8-38.1 dB(A)
- Power: from 1.0 W
- Diameter: 154 mm

**Silvento ec (extract only):**
- Airflow: 15-60 m3/h (up to 100 m3/h)
- Sound: 22 dB(A) at 15 m3/h, 35 dB(A) at 60 m3/h
- Power: 1.8-6.2 W
- Optional humidity/VOC sensors on comfort+ board

#### Airflow Calculation

With 5 pairs of e2 60 (10 units) at level 2: 10 x 32 = **320 m3/h**
At level 3: 10 x 38 = **380 m3/h**

**Verdict:** Easily meets both targets. Could even use fewer units.

#### Pricing (EUR from Partel Europe shop)

| Product | Price (EUR incl. VAT) |
|---|---|
| e2 60 (1 pair incl. transformer + controller) | 1,756 |
| ego (single unit, incl. transformer + controller) | 1,014 |
| Silvento ec (extract fan) | from 446 |
| Smart Comfort 5/SC-FT controller | 204 |
| Wireless screen (optional) | 216 |

**Estimated total for 5 pairs e2 60 + 3 ego:** 5 x 1,756 + 3 x 1,014 = **11,822 EUR**
**Or 5 pairs e2 60 + 3 Silvento ec:** 5 x 1,756 + 3 x 446 = **10,118 EUR**

This is 2-3x the cost of Blauberg.

#### Home Assistant Integration - POOR (requires hardware hacking)

Lunos has **no smart/connected controller**. All integration requires custom hardware:

1. **0-10V analog control** - The 5/UNI-FT controller accepts 0-10V input. Can use:
   - [Monarco HAT](https://github.com/cyaneous/hass-monarco) (RPi HAT with analog outputs)
   - Shelly Plus 0-10V Dimmer
2. **ESPHome with DAC** - m5stack Atom Lite + DAC2 module to generate 0-10V signal. [Documented config](https://gist.github.com/cyaneous/e95b80966185376e6787ebbdb4484068).
3. **Smart relay approach** - The W1/W2 switch inputs on the controller can be replaced with smart relays (Shelly, Sonoff). [HACS integration](https://github.com/rsnodgrass/hass-lunos) maps HA commands to W1/W2 states.
4. **SC-FT controller** - The newer Smart Comfort controller has humidity/temperature sensors and manages up to 10 units, but still no network connectivity. A community member is [exploring integration](https://community.home-assistant.io/t/lunos-sc-ft-control-integration/710456).

**Bottom line:** Works, but requires soldering/wiring custom hardware. Not plug-and-play.

#### Controller Options

- **5/UNI-FT:** Basic controller per pair, 4 speed levels + summer mode + exhaust only. 0-10V input for external control.
- **Smart Comfort 5/SC-FT:** Up to 10 units, humidity/temperature sensors, 8 automatic levels, night reduction, summer mode. 204 EUR. Still no network/app.

#### Reliability - EXCELLENT

- Established since 1951, Berlin manufacturer
- Ceramic heat storage cores are virtually indestructible
- Users report 10+ years trouble-free operation (one user: since 2013, no issues)
- Passive House certified (e2 60)
- Well-documented maintenance: pull cores once/year for cleaning
- Known issue: audible cycling sound (fan reversal every ~70s) - noticeable at night for light sleepers

---

### 3. InVENTer (iV-Smart+, iV-Twin+, iV14-Zero)

**Origin:** Germany (InVENTer GmbH, Thuringia)

#### Models

| Model | Type | Airflow | Use Case |
|---|---|---|---|
| iV-Smart+ | Push-pull HRV (paired) | 5-21 m3/h (HRV), 10-42 m3/h (extract) | Standard rooms |
| iV-Smart+ Connect | Push-pull HRV (paired, wireless) | Same as Smart+ | Smart-enabled rooms |
| iV-Twin+ | Dual-fan single unit (standalone) | 5-23 m3/h (HRV), 10-45 m3/h (extract) | Standalone rooms, bathrooms |
| iV14-Zero | Push-pull HRV (paired, sound-optimized) | 8.5-29 m3/h (HRV) | Bedrooms, quiet rooms |

#### Specifications

**iV-Smart+:**

| Parameter | Min | Max |
|---|---|---|
| Airflow (HRV mode) | 5 m3/h | 21 m3/h |
| Airflow (extract mode) | 10 m3/h | 42 m3/h |
| Sound at 2 m | 14 dB(A) | 36 dB(A) |
| Sound insulation | 34-47 dB | |
| Power consumption | 1 W | 3 W |

- Heat recovery: 84% (87% claimed on some sources)
- Energy class: A+/A
- Wall opening: 180 mm
- Min wall thickness: 140 mm
- Fan voltage: 6-16V DC

**iV-Twin+:**

| Parameter | Min | Max |
|---|---|---|
| Airflow (HRV mode) | 5 m3/h | 23 m3/h |
| Airflow (extract mode) | 10 m3/h | 45 m3/h |
| Sound at 2 m | 14 dB(A) | 38 dB(A) |
| Sound insulation | up to 56 dB | |
| Power consumption | - | 3 W |

- Heat recovery: 94% - highest in its class
- Energy class: A+
- Single unit, no pairing needed (two fans in one tube)
- Wall opening: 100 mm (smallest of all brands)

**iV14-Zero:**
- Airflow: 8.5-29 m3/h (HRV mode)
- Heat recovery: 87%
- Sound insulation: up to 56 dB
- Sound emission: from 10 dB(A) (whisper mode)
- Wall opening: 225 mm
- Min wall thickness: 255 mm

#### Airflow Calculation

With 10 iV-Smart+ units at max HRV: 10 x 21 = **210 m3/h**
With 10 iV-Smart+ at max extract: 10 x 42 = **420 m3/h**

**Verdict:** Just barely meets 190 m3/h at max speed in HRV mode. Would need to use extract mode (no heat recovery) for boost. The low per-unit HRV airflow is a significant limitation. Could consider mixing iV-Smart+ (rooms) with iV-Twin+ (bathrooms).

#### Pricing (EUR from German retailers)

| Product | UVP (EUR) | Street Price (EUR) |
|---|---|---|
| iV-Smart+ Komplettset | 773 | ~742 |
| iV-Twin+ Komplettset | 1,050 | ~794-1,008 |
| iV14-Zero Komplettset | 875 | ~840 |
| sMove s4 controller (4 units) | ~200 | ~180 |
| sMove s8 controller (8 units) | ~300 | ~270 |

**Estimated total for 7x iV-Smart+ + 3x iV-Twin+:** 7 x 742 + 3 x 1,008 + controllers = **~8,700 EUR**

#### Home Assistant Integration - POOR

The situation is fragmented:

1. **sMove controller has 0-10V interface** - Can connect a Shelly Plus 0-10V Dimmer to Interface 2 for HA control. [Documented approach](https://community.home-assistant.io/t/controlling-an-inventer-smove-decentralized-ventilation-system-via-ha-and-shelly/796906).
2. **InVENTer Connect (newer system)** - Bluetooth-based with "inVENTer Mobile" app and Easy-Connect controller (up to 16 units, 4 zones). However, **no HA integration exists**. Uses proprietary RF 868 MHz between units and Bluetooth to app.
3. **No local API, no Modbus, no WiFi** - The Easy Control e16 uses RF 868 MHz + Bluetooth only. [HA community confirms no integration](https://community.home-assistant.io/t/looking-for-inventer-easy-control-e16-ha-integration/857319).
4. **Shelly 0-10V is the only viable path** for HA integration.

#### Controller Options

- **sMove s4:** Controls up to 4 units, capacitive touch buttons, 4 preset speeds + variable. One sensor input (humidity OR CO2 OR VOC). 0-10V external input.
- **sMove s8:** Controls up to 8 units.
- **Easy-Connect:** Up to 16 units, 4 zones, app control via Bluetooth, humidity/temperature/CO2 display. No HA integration.

#### Reliability - GOOD

- German manufacturer, established brand
- Well-regarded in Passive House community
- Ceramic cores like Lunos
- 70-second reversing cycle
- Less community feedback available than Lunos

---

### 4. Prana (150 series)

**Origin:** Ukraine (Prana UA)
**Note:** Prana is NOT a push-pull paired system. Each unit has two separate fans (supply + extract) running simultaneously through a single wall penetration. This is technically a single-unit balanced system, not a push-pull.

#### Models

| Model | WiFi | Sensors | Price Tier |
|---|---|---|---|
| Prana 150 Standard | No | No | Budget |
| Prana 150 Eco Life | No | Basic | Mid |
| Prana 150 Eco Energy | Yes | Temp, humidity, pressure | Mid-premium |
| Prana 150 Premium Plus | Yes | Temp, humidity, pressure, CO2, TVOC | Premium |
| Prana 150 Carbon (WiFi) | Yes | Full suite | Premium |

**No separate bathroom model** - each unit is self-contained with both supply and extract.

#### Specifications (Prana 150)

| Parameter | Night | Speed 1 | Speed 2 | Speed 3 | Speed 4 | Speed 5 | Boost |
|---|---|---|---|---|---|---|---|
| Airflow (m3/h) | ~12 | 5 | 14 | 21 | 32 | 52 | 70* |

*Boost is unregulated, not for continuous use

- **Heat recovery:** up to 95-98% (manufacturer claim - likely inflated)
- **Sound at 3 m:** from 8 dB(A) (night) to ~52 dB(A) (max)
- **Power consumption:** 3.2-17 W (up to 51 W with mini-heater)
- **Wall opening:** 162 mm
- **Module length:** from 450 mm
- **Copper heat exchanger** (antibacterial properties)
- **Operating temperature:** -30 to +40 C (mini-heater activates below +14 C)

#### Airflow Calculation

With 10 units at speed 3: 10 x 21 = **210 m3/h**
At speed 4: 10 x 32 = **320 m3/h**
At speed 5: 10 x 52 = **520 m3/h**

**Verdict:** Meets targets easily, though manufacturer specs may be optimistic.

#### Pricing (EUR)

| Source | Model | Price (EUR) |
|---|---|---|
| Estonian retailer | Prana 150 Standard | 723 |
| Estonian retailer | Prana 150 Premium Plus | ~900 |
| Latvian distributor | Prana range | from 515 |

**Estimated total for 10 Eco Energy units:** ~6,000-7,500 EUR

#### Home Assistant Integration - GOOD (official integration since 2026.2)

1. **Official HA integration (2026.2)** - `prana` integration, IoT class: **Local Polling**. Requires device on same network.
2. **Custom integrations:**
   - [ha-prana](https://github.com/alextud/ha-prana) - Bluetooth-based
   - [homeassistant_prana](https://github.com/corvis/homeassistant_prana) - Uses prana_rc library
   - [prana-wifi](https://github.com/boot-nyxpoint/prana-wifi) - Cloud API based (polls every 15s)
3. **Control options:** Fan speed 0-5, presets, temperature/humidity/CO2/TVOC sensors, display brightness

#### Reliability - MIXED

- Ukrainian manufacturer - supply chain concerns given ongoing conflict
- Copper heat exchanger is more fragile than ceramic
- 2-year warranty (shorter than German brands)
- Efficiency claims (up to 98%) appear inflated compared to certified European tests
- Less established track record than German manufacturers
- On the positive side: CE certified, available in 42+ countries

---

### 5. Meltem (M-WRG-II series)

**Origin:** Germany (Meltem Warmeruckgewinnung GmbH)
**Positioning:** Premium/professional - primarily for multi-unit residential buildings and hotels

#### Models

| Model | Type | Notes |
|---|---|---|
| M-WRG-II P | Push-pull, plate heat exchanger | Basic model |
| M-WRG-II E | Push-pull, enthalpy exchanger | Moisture recovery |
| M-WRG-II E-F | Enthalpy + fine dust filter | |
| M-WRG-II E-FC | Enthalpy + fine dust + CO2 sensor | Premium |
| M-WRG-II E-T | Enthalpy + temperature sensor | |
| M-WRG-II E-M | Enthalpy + multi-sensor | |

#### Specifications

| Parameter | Min | Max |
|---|---|---|
| Airflow (continuous) | 10 m3/h | 51 m3/h |
| Airflow (boost) | 10 m3/h | 77 m3/h |
| Heat recovery | - | 94% |
| Sound insulation | 54 dB | 70 dB |
| Power consumption | ~2 W | ~12 W |

- Passive House certified
- Available in surface-mount, flush-mount, and fully integrated (invisible) versions
- Can ventilate multiple rooms from a single unit (unique feature)
- Constant volume flow rate control

#### Pricing (EUR from German retailers)

| Model | UVP (EUR) | Street Price (EUR) |
|---|---|---|
| M-WRG-II E-T | 1,858 | 1,465 |
| M-WRG-II E-F | 1,867 | 1,491 |
| M-WRG-II E-M | 1,946 | 1,571 |
| M-WRG-II E-FC | 2,061 | 1,657 |

**Estimated total for 10 units:** ~15,000-16,000 EUR

This is by far the most expensive option.

#### Home Assistant Integration - GOOD (via Modbus gateway)

1. **Meltem Gateway (M-WRG-GW)** - Connects to units via WiFi/Ethernet, exposes **Modbus RTU** via USB. [Active HA community thread](https://community.home-assistant.io/t/meltem-wrg-ii-integration-via-meltem-gateway-and-modbus/720906).
2. **KNX gateway (M-WRG-KNX-GW)** - For KNX bus integration, works with HA's KNX integration.
3. **Loxone, ioBroker** also supported.

#### Reliability - EXCELLENT

- German engineering, premium build quality
- Passive House certified
- Best sound insulation in the market (up to 70 dB)
- Used in professional multi-unit buildings

**Verdict:** Overkill for a single-family house. Price is prohibitive. But the Modbus gateway and sound insulation are best-in-class.

---

### 6. Helios (KWL EC 60 series)

**Origin:** Germany (Helios Ventilatoren)

#### Models

| Model | Type | Features |
|---|---|---|
| KWL EC 60 Eco | Single-room HRV | Basic, aluminum heat exchanger |
| KWL EC 60 Pro | Single-room HRV | Comfort control element |
| KWL EC 60 Pro FF | Single-room HRV | Comfort control + humidity sensor |

#### Specifications

| Parameter | Speed 1 | Speed 2 | Speed 3 | Speed 4 |
|---|---|---|---|---|
| Airflow | 17 m3/h | 30 m3/h | 45 m3/h | 60 m3/h |
| Sound at 3 m | 18 dB(A) | 22 dB(A) | 29 dB(A) | 30 dB(A) |
| Power consumption | ~3 W | ~6 W | ~10 W | 14 W |

- **Heat recovery:** >70% (aluminum plate exchanger) - significantly lower than ceramic competitors
- **Voltage:** 230V/50Hz (mains powered, not SELV)
- **4 speed levels** - more granular than most competitors

**Note:** Helios uses an aluminum plate heat exchanger, not ceramic. This means lower efficiency (70%) compared to ceramic units (85-96%). The aluminum exchanger is a continuous counter-flow design (not push-pull with storage), which means no cycling/direction reversal noise but lower per-unit efficiency.

#### Pricing (EUR from German retailers)

| Model | Price (EUR) |
|---|---|
| KWL EC 60 Eco | ~920-1,050 |
| KWL EC 60 Pro | ~1,180 |
| KWL EC 60 Pro FF (humidity) | ~1,273 |

**Estimated total for 10 units (mix of Pro and Pro FF):** ~11,000-12,000 EUR

#### Home Assistant Integration - MODERATE

1. **ESPHome via PWM** - [Community project](https://community.home-assistant.io/t/esphome-controller-for-decentralized-helios-ventilation-kwl-pwm/868194) for PWM-controlled decentralized units.
2. **RS485** - Some models have RS485. [ESPHome integration](https://github.com/lostcontrol/esphome-helios-kwl) available.
3. **Helios EasyControls** - For centralized KWL units only (Modbus TCP/IP). The decentralized EC 60 does NOT have EasyControls.
4. **Custom HACS component** - [asev/homeassistant-helios](https://github.com/asev/homeassistant-helios) tested mainly on centralized KWL 300/340.

**Bottom line:** The decentralized KWL EC 60 has limited smart home options. RS485 or PWM via ESPHome is the main path.

#### Reliability - GOOD

- Helios is a major German ventilation manufacturer
- Well-established in European market
- Less community feedback on decentralized models specifically

**Verdict:** Low efficiency (70%) is a dealbreaker compared to ceramic competitors offering 85-96%. Expensive for what you get. Better suited for projects already committed to the Helios ecosystem.

---

### 7. Other Brands Considered

#### Stiebel Eltron VLR 70

- **Type:** Push-pull, paired operation
- **Airflow:** 20/30/40/49/70 m3/h (5 speeds)
- **Heat recovery:** up to 92%
- **Sound:** 35 dB(A) at 20 m3/h
- **Power:** 2-12 W at 24V
- **Price:** ~429 EUR per unit (German retailer, but often out of stock)
- **Controller:** Up to 8 units per user interface
- **HA integration:** Limited. ISG gateway exists for heat pumps but decentralized VLR 70 has no documented integration path.
- **Verdict:** Good specs but unclear availability and poor smart home support.

#### Zehnder ComfoSpot 50

- **Type:** Push-pull with enthalpy heat exchanger
- **Heat recovery:** up to 82% (heat) + 70% (humidity)
- **Airflow:** up to 50 m3/h
- **Key advantage:** Enthalpy exchanger recovers moisture - no condensation
- **Price:** ~810-980 EUR per unit (German retailers)
- **HA integration:** Possible via RFZ module networking, but not well documented
- **Estimated total for 10 units:** ~8,000-10,000 EUR
- **Verdict:** Good unit but expensive, mediocre HA integration.

#### Vents TwinFresh (same protocol as Blauberg)

- **Note:** Vents (Ukrainian parent) makes the TwinFresh series which uses the **same Modbus UDP protocol** as Blauberg Vento Expert
- **Models:** TwinFresh Comfo RA1-50, TwinFresh Expert, TwinFresh Elite, TwinFresh Atmo
- **TwinFresh Elite** has built-in temperature, humidity, CO2eq, air quality sensors + electric heater + app
- **HA integration:** Same ecovent integration as Blauberg works with TwinFresh units
- **Verdict:** Worth considering as alternative to Blauberg since same protocol/integration. May be cheaper in some markets.

#### Marley MEnV180 (Germany)

- **Type:** Push-pull, paired
- **Sound:** 39 dB(A) operating
- **Coverage:** ~20 m2 per unit
- **Price:** Not widely available
- **HA integration:** None found
- **Verdict:** Niche product, limited availability, no smart home support.

---

## Comparison Matrix

| Criteria | Blauberg A50-1 W | Lunos e2 60 | InVENTer iV-Smart+ | Prana 150 EE | Meltem M-WRG-II | Helios KWL EC 60 |
|---|---|---|---|---|---|---|
| **Price per unit (EUR)** | ~500-590 | ~878 (per unit from pair) | ~742 | ~600-750 | ~1,500 | ~1,000-1,200 |
| **10 units total (EUR)** | ~5,000-5,900 | ~10,000-12,000 | ~8,700 | ~6,000-7,500 | ~15,000 | ~11,000 |
| **Heat recovery %** | 93% | 90-96% | 84-94% | 95%* | 94% | >70% |
| **Airflow per unit (HRV)** | 8-25 m3/h | 15-60 m3/h | 5-21 m3/h | 5-52 m3/h | 10-51 m3/h | 17-60 m3/h |
| **Sound at normal** | 18 dB(A) @ 3m | 19.5 dB(A) @ 3m | 14-36 dB(A) @ 2m | ~20-25 dB(A) | N/A detailed | 22 dB(A) @ 3m |
| **HA integration** | Excellent (local Modbus UDP) | Poor (hardware hack) | Poor (0-10V only) | Good (official since 2026.2) | Good (Modbus via gateway) | Moderate (ESPHome/RS485) |
| **Bathroom model** | W variant with humidity | ego / Silvento ec | iV-Twin+ | Same unit | Same unit | Pro FF (humidity) |
| **Pairing required** | Yes (WiFi sync) | Yes (wired to controller) | Yes (wired to sMove) | No (standalone) | No | No |
| **Wall opening** | 160 mm | 154 mm | 180 mm | 162 mm | varies | varies |
| **Min wall thickness** | ~300 mm | 300 mm | 140 mm | ~450 mm | ~280 mm | ~300 mm |
| **Controller** | App (WiFi) | SC-FT (wired) | sMove/Easy-Connect | App (WiFi/BT) | Gateway (Modbus) | Wall panel |
| **Origin** | DE/UA | DE | DE | UA | DE | DE |
| **Reliability** | Good | Excellent | Good | Mixed | Excellent | Good |

*Prana efficiency claims appear inflated vs independent testing

---

## Recommendations

### Best Overall: Blauberg Vento Expert A50-1 W V.3

**Why:**
- Best price-to-feature ratio (~5,500 EUR for 10 WiFi units)
- Excellent HA integration via local Modbus UDP - no cloud, no hacking needed
- Multiple proven HACS integrations
- Slovenian distributor available (blauberg.si)
- WiFi synchronization handles paired operation automatically
- Humidity sensor in W models handles bathroom boost

**Concerns:**
- Lower per-unit HRV airflow (25 m3/h max) - compensated by having 10 units
- Ukrainian parent company (but German subsidiary, CE certified, EU production)
- Less track record than Lunos

### Runner-Up: Lunos e2 60

**Why:**
- Best build quality and acoustics
- Highest efficiency (up to 96%)
- 25+ year track record
- Passive House certified
- Best sound insulation (67 dB)

**Why not for this project:**
- 2-3x the cost of Blauberg
- Requires hardware hacking for HA integration (no native network connectivity)
- SC-FT controller has no API/network interface

### Worth Considering: Prana 150 Eco Energy

**Why:**
- Official HA integration (local polling, no cloud)
- Each unit is self-contained (no pairing needed)
- Built-in sensors (temperature, humidity, pressure)
- Reasonable price

**Why not:**
- Unproven long-term reliability vs German brands
- Inflated efficiency claims
- Ukrainian supply chain risk
- Copper exchanger less durable than ceramic

---

## Open Questions

1. **Wall thickness verification** - Need to confirm exterior wall thickness is >=300 mm for Blauberg/Lunos compatibility. InVENTer only needs 140 mm (advantage for thinner walls).
2. **Blauberg W V.3 vs V.2** - Is V.3 available from the Slovenian distributor? V.3 may have improved firmware/WiFi stack.
3. **Bathroom rating** - None of these push-pull units are IP-rated for direct bathroom installation. Need to verify if humidity-sensing models are sufficient or if a separate extract fan (like Lunos Silvento) is needed for wet rooms.
4. **Wind exposure** - Slovenian forum users report cold drafts and reduced efficiency on windy days. Need wind-exposed wall assessment per room.
5. **Blauberg HA integration maturity** - Test one unit first to verify the ecovent_v2 HACS integration works reliably with V.3 firmware before ordering all 10.
6. **Noise assessment** - Visit a showroom or request a demo unit. The 70-second cycling of push-pull units is the #1 complaint in forums.
7. **Blauberg.si pricing** - Contact the Slovenian distributor for actual pricing (may differ from German online shops).

---

## Sources

### Blauberg
- [Blauberg DE - Vento Expert A50-1 Pro](https://blaubergventilatoren.de/en/product/vento-expert-a50-1-pro)
- [Blauberg Slovenia](https://www.blauberg.si/lokalne-prezracevalne-naprave/vento-expert)
- [skybad.de - Blauberg pricing](https://www.skybad.de/en/blauberg-vento-expert-8020667-a50-1-pro-dezentrale-lueftung-ohne-wlan-steuerung.html)
- [ecovent_v2 HA integration](https://github.com/gody01/ecovent_v2)
- [hass-ecovent](https://github.com/49jan/hass-ecovent)
- [Blauberg HA integration Docker](https://github.com/gracingpro/blauberg-homeassistant)
- [MQTT bridge (BITK)](https://blomkvistitk.no/produkt/fan2mqtt-mqtt2fan-licenses/?lang=en)

### Lunos
- [Lunos e2 product page](https://www.lunos.de/en/all-products/e2)
- [Lunos e2 60 product page](https://www.lunos.de/en/all-products/e260)
- [Lunos ego product page](https://www.lunos.de/en/all-products/ego)
- [Partel Europe shop (EUR pricing)](https://shopeu.partel.com/collections/lunos)
- [hass-lunos HA integration](https://github.com/rsnodgrass/hass-lunos)
- [ESPHome Lunos control](https://gist.github.com/cyaneous/e95b80966185376e6787ebbdb4484068)
- [Lunos SC-FT HA discussion](https://community.home-assistant.io/t/lunos-sc-ft-control-integration/710456)
- [HA community - Lunos HRV control](https://community.home-assistant.io/t/lunos-heat-recovery-ventilation-hrv-fan-control/157287)
- [Lunos e2 Rise review](https://www.buildwithrise.com/stories/lunos-e2-ductless-hrv-system-technical-overview-performance-installation-guide)

### InVENTer
- [InVENTer iV-Smart+ Canada specs](https://inventercanada.com/products/iv-compact)
- [InVENTer iV-Twin+ Canada specs](https://inventercanada.com/products/iv-twin)
- [InVENTer product overview](https://www.inventer.eu/products/heat-recovery/overview/)
- [InVENTer Connect](https://www.inventer.eu/connect/)
- [sMove controller](https://www.inventer.eu/products/controller/smove/)
- [HA - InVENTer sMove + Shelly integration](https://community.home-assistant.io/t/controlling-an-inventer-smove-decentralized-ventilation-system-via-ha-and-shelly/796906)
- [HA - InVENTer easy control e16 (no integration)](https://community.home-assistant.io/t/looking-for-inventer-easy-control-e16-ha-integration/857319)

### Prana
- [Prana product page (UA)](https://prana.ua/en/products/prana150ee/)
- [Estonian retailer pricing](https://ventilaatorid24.ee/product/prana-150/?lang=en)
- [Official HA integration](https://www.home-assistant.io/integrations/prana)
- [ha-prana custom integration](https://github.com/alextud/ha-prana)
- [prana-wifi integration](https://github.com/boot-nyxpoint/prana-wifi)
- [homeassistant_prana](https://github.com/corvis/homeassistant_prana)

### Meltem
- [Meltem M-WRG-II product page](https://www.meltem.com/en/products/m-wrg-ii/)
- [HA - Meltem Modbus integration](https://community.home-assistant.io/t/meltem-wrg-ii-integration-via-meltem-gateway-and-modbus/720906)
- [Meltem technical data PDF](https://www.meltem.com/fileadmin/downloads/documents/Meltem%20technical%20data%20M-WRG-II%20EN.pdf)

### Helios
- [Helios KWL EC 60 Pro FF](https://www.heliosventilatoren.de/en/products/ventilation-with-heat-recovery/single-room-ventilation-units/en-kwl-ec-60-pro-ff-09957)
- [ESPHome Helios KWL PWM](https://community.home-assistant.io/t/esphome-controller-for-decentralized-helios-ventilation-kwl-pwm/868194)
- [homeassistant-helios HACS](https://github.com/asev/homeassistant-helios)

### Stiebel Eltron
- [VLR 70 S Trend](https://www.stiebel-eltron.com/en/home/products-solutions/renewables/ventilation/decentralised/vlr-70-s-l-trend/vlr-70-s-trend-en.html)

### Zehnder
- [ComfoSpot 50](https://www.international.zehnder-systems.com/en/comfortable-indoor-ventilation/products/units/decentralised-ventilation-units/zehnder-comfospot-50)

### General
- [Best Ductless ERVs/HRVs 2025 (Rise)](https://www.buildwithrise.com/stories/best-ductless-ervs-hrvs-2025)
- [Slovenian forum - local HRV discussion](https://www.podsvojostreho.net/forum/showthread.php?tid=70093)
- [Green Building Advisor - decentralized shortcomings](https://www.greenbuildingadvisor.com/question/decentralized-ventilation-shortcomings)
