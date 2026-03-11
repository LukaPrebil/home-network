# Master Guide: Orca Heat Pump Smart Home Integration

**Goal:** Achieve zero-cloud, local Home Assistant integration for deep data monitoring (via Modbus) and automated solar-soaking (via SG-Ready).

## 1. Hardware Shopping List

* **1x Shelly 1 Gen4:** For the SG-Ready "Solar Dump" switch.
* **1x Elfin EW11A (RS485 to Wi-Fi):** For the Modbus data stream.
* **1x Mean Well HDR-15-12 (or 24):** A DIN-rail 12V/24V DC power supply to power the Elfin.
* **1x Scrap Ethernet Cable (CAT5e/CAT6):** For the RS485 twisted-pair data connection.
* **Electrical Wire:** Standard gauge wire for connecting the 230V AC power.

---

## 2. Physical Layout & Power Strategy

**⚠️ CRITICAL RULE:** Do not pull power from the sensitive `+Vdc` or `24V` pins on the green Carel logic board. All smart home equipment must be powered directly from the heat pump's main 230V incoming power block.

### A. Powering the Devices

Mount the Mean Well power supply, the Shelly, and the Elfin onto the internal DIN rail.

1. **Mean Well (for Elfin):** Wire `L1` and `N` from the heat pump's main 230V power block into the TOP of the Mean Well.
2. **Shelly 1 Gen4:** Wire `L1` and `N` from the main 230V power block to the `L` and `N` terminals on the Shelly.
3. **Elfin EW11A:** Wire the DC output (+ and -) from the BOTTOM of the Mean Well into the `VCC` (Pin 7) and `GND` (Pin 8) of the Elfin's green connector.

---

## 3. The Control Wiring

### A. The "Solar Dump" Switch (Shelly 1 Gen4)

The Shelly uses its "Dry Contact" relay to safely trigger the Carel board's factory SG-Ready mode without sending voltage into the logic board.

* Connect Shelly **`I` (Input)** ➔ Carel Board **`ID9`** (or `PV`).
* Connect Shelly **`O` (Output)** ➔ Carel Board **`GND`** (the pin directly next to `ID9`).

### B. The Modbus Data Connection (Elfin EW11A)

Strip your Ethernet cable and isolate **ONE twisted pair** (e.g., Solid Blue and Striped White/Blue) plus one extra ground wire (e.g., Solid Brown).

* **Positive Data:** Solid Blue wire ➔ Elfin **`A+`** (Pin 5) to Carel **`R+`** (or `Tx/Rx+`).
* **Negative Data:** Striped White/Blue wire ➔ Elfin **`B-`** (Pin 6) to Carel **`T-`** (or `Tx/Rx-`).
* **Ground (Mandatory):** Solid Brown wire ➔ Elfin **`GND`** (Pin 8) to Carel **`GND`** (next to `R+/T-`).

---

## 4. Software Setup & macOS Tools

### A. Elfin EW11A Configuration

Connect to the Elfin's temporary Wi-Fi network, navigate to its IP address (usually `11.22.33.44`), and apply these exact settings so it can translate for the Carel pCO board:

* **Baud Rate:** `19200`
* **Data Bits:** `8`
* **Parity:** `None` *(Fallback to `Even` if it fails)*
* **Stop Bits:** `1` *(Fallback to `2` if it fails)*
* **Protocol:** `Modbus` *(Do not use Transparent/None)*
* **Local Port:** `502`
* Connect it to your main home Wi-Fi and note its new local IP address (e.g., `192.168.1.50`).

### B. The macOS Scanning Tools

Download one of these free, open-source tools to connect to the Elfin from your Mac:

1. **QModMaster** (Highly recommended GUI)
2. **OpenModScan** (Great for sweeping large blocks of addresses)
*Set your tool to connect via **Modbus TCP** to the Elfin's IP address on port `502`.*

---

## 5. The Modbus Register "Hunt" List

When you start scanning, the Carel board will spit out hundreds of numbers. Use this hit-list to know what to look for.

*Tip: Carel usually scales temperatures by 10 (e.g., 45.2°C shows up as `452`).*

### Group 1: Live Sensors (Read-Only / Input Registers)

*Look in the `30000` range.*

* **OT (Outdoor Temperature):** Check outside weather, look for matching number.
* **TB (Sanitary Water Bottom):** The core temp of your 200L tank.
* **LB (Sanitary Water Top):** The delivery temp of your shower water.
* **TM1 (Inlet 1 / Flow Temp):** The hot water going *into* your floors.
* **TM2 (Inlet 2 / Return Temp):** The cooled water coming *back* from the floors.

### Group 2: Target Settings (Read/Write / Holding Registers)

*Look in the `40000` range. Stand at the basic screen, change a value, and watch which register changes on your Mac.*

* **DHW Target Temp:** Change hot water target from 45°C to 46°C. Look for `450` changing to `460`.
* **Heating Target / Weather Curve Offset:** Change your room target by 1 degree.
* **Mode Switch:** Switch from Winter (Heating) to Summer (Hot Water Only). Look for a register flipping between `0`, `1`, or `2`.

### Group 3: Hardware Status (Binary / Coils / Discrete Inputs)

*Look in the `00000` or `10000` ranges. These are simple `1` (On) or `0` (Off) switches.*

* **3-Way Valve State:** Flips when the heat pump switches from underfloor heating to the 200L water tank.
* **PUMP P0 State:** Is the main water circulation pump running?
* **Compressor Status:** Is the outdoor Mitsubishi unit actively running?
* **Defrost Cycle:** Turns to `1` when the outdoor unit is melting ice (Great to track for Home Assistant dashboards!).
* **PV Input Status:** This should turn to `1` the moment your Shelly relay closes.
* **Error / Alarm Flag:** Flips to `1` if there is a Flow Error or sensor failure.


## 6. Home Assistant YAML Integration

Once you have successfully hunted down and mapped your register numbers using the macOS scanning tools, you do not need any custom HACS integrations. You will use Home Assistant's native Modbus integration by editing your `configuration.yaml` file.

### A. The Core Modbus Connection

Add this block to tell Home Assistant how to talk to your Elfin EW11A over the network.

```yaml
modbus:
  - name: orca_heatpump
    type: tcp
    host: 192.168.1.50 # Change this to your Elfin's actual IP address
    port: 502

```

### B. Adding Sensors (Reading Temperatures)

Under the core connection, add the `sensors:` block. This is for the live data you found in the `30000` range (Input Registers).

**The Scaling Rule:** Carel stores temperatures scaled by 10 (e.g., 45.2°C is `452`). You must use `scale: 0.1` to convert it back to a readable decimal.

```yaml
    sensors:
      - name: "Orca Tank Temperature (Bottom)"
        unique_id: orca_tank_temp_bottom
        address: 15 # Replace with your mapped register number
        input_type: input # Tells HA this is a 3xxxx register
        unit_of_measurement: °C
        device_class: temperature
        state_class: measurement
        scale: 0.1
        precision: 1

```

### C. Adding Controls (Writing Targets)

For settings you want to change from Home Assistant (like your target hot water temperature from the `40000` Holding Registers range), use the `numbers:` block instead of sensors. Home Assistant will automatically multiply your input by 10 before sending it to the heat pump.

```yaml
    numbers:
      - name: "Orca Target Hot Water Temp"
        unique_id: orca_target_dhw
        address: 45 # Replace with your mapped register number
        input_type: holding # Tells HA this is a 4xxxx register
        unit_of_measurement: °C
        min_value: 35.0
        max_value: 55.0
        scale: 0.1
        step: 0.5

```

### D. Adding Status Switches (Binary Sensors)

For the simple On/Off hardware states (like the Compressor or Defrost cycle from the `00000` or `10000` ranges), use the `binary_sensors:` block.

```yaml
    binary_sensors:
      - name: "Orca Compressor Running"
        unique_id: orca_compressor_status
        address: 5 # Replace with your mapped register number
        input_type: discrete_input # Use 'coil' if it is in the 0xxxx range
        device_class: running

```

### E. ⚠️ The "Zero-Based Indexing" Trap

When moving your mapped numbers from the scanner tool into Home Assistant YAML, remember two rules:

1. **Drop the prefix:** If your scanner says holding register `40016`, do not type `40016`. The `input_type: holding` command already handles the `40000` part. You just type `16`.
2. **Subtract One (Sometimes):** Many manuals and scanners start counting at 1, but Modbus code starts counting at 0. If you type `address: 16` and it doesn't work or gives you the wrong data, change it to `address: 15`.

### F. Activating the Configuration

1. In Home Assistant, navigate to **Developer Tools** > **YAML**.
2. Click **Check Configuration** to ensure your spacing is correct.
3. If it passes, click **Restart** (or reload the Modbus integration).
4. Your heat pump entities will immediately appear in your device list, ready for your dashboards!


## 7. Automated Modbus Register Hunting (For AI Agents / Claude Code)

**Note to AI Agent:** This section contains your instructions. The user is attempting to reverse-engineer undocumented Modbus registers on a Carel pCO industrial logic board (used in an Orca Heat Pump). You cannot use GUI tools like QModMaster. You must build a CLI-based Python tool to help the user hunt for specific registers.

### A. The Environment & Target

* **Target IP:** `192.168.1.160` (Elfin EW11's IP on the home network).
* **Target Port:** `502` (Modbus TCP).
* **Dependency:** `pymodbus` 3.12+ is installed in `.venv/` — use `.venv/bin/python3`.
* **Board:** Custom Carel OEM (CODE B02563), requires **PCOS004850 BMS card** for Modbus slave access. See `docs/hardware/orca-modbus-findings.md` for full investigation notes.
* **Hardware Quirk:** The Carel board is slow. Ensure your Modbus timeout settings are generous (at least 2-3 seconds) and do not poll too aggressively, or the Elfin bridge will drop packets.

### B. Your Task: The "Diff" Script

Write and execute a Python script that performs a "diff" on Modbus registers to isolate exactly which register controls a specific function. The script must follow this exact logic:

1. **Connect:** Establish a `ModbusTcpClient` connection to the target IP.
2. **Snapshot A:** Read a block of registers (e.g., Holding Registers 1 through 100) and store the values in memory. Ignore or catch `ModbusIOException` errors for empty/unmapped registers, as Carel boards often have gaps in their memory maps.
3. **The Human Pause:** Pause the script and print a prompt to the terminal: *"Snapshot A taken. Please go physically change the target setting on the heat pump screen, wait 5 seconds, and then press ENTER here."*
4. **Snapshot B:** Once the human presses Enter, read that exact same block of registers again.
5. **The Diff:** Compare Snapshot A to Snapshot B.
6. **Output:** Print *only* the registers whose values changed, displaying the Register Number, the Old Value, and the New Value.

### C. Search Ranges & Context to Keep in Mind

When prompting the human to find specific types of data, use these standard Carel ranges:

* **To find Live Temperatures (Read-Only):** Scan **Input Registers** (the `30000` range, function code 04).
* **To find Target Settings (Read/Write):** Scan **Holding Registers** (the `40000` range, function code 03).
* **To find Status Switches (On/Off):** Scan **Coils / Discrete Inputs** (the `00000` or `10000` ranges, function codes 01 or 02).

### D. Data Parsing Rules (Crucial)

When you output the final YAML configuration for the user's Home Assistant setup, you must apply these two rules:

1. **Carel Temperature Scaling:** Carel stores temperatures as integers scaled by 10 (e.g., `45.2°C` is stored as `452`). When generating Home Assistant YAML, you must include `scale: 0.1` for temperature entities.
2. **Zero-Based Indexing:** Depending on how you configure `pymodbus`, the raw address might be 0-indexed. If the user's heat pump manual says "Register 15", the actual Modbus wire address is usually `14`. Ensure you confirm the exact offset being used so the Home Assistant YAML `address:` field is accurate.