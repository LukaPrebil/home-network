# Solar Installation & Site Visit Master Checklist

## 1. Cable Routing: Roof to Utility Room (The Vapor Barrier Plan)
*Goal: Route heavy DC cables from the roof to the inverter without breaching the exterior thermal envelope.*
* **The Route:** Use the vertical installation shaft next to the vent pipe (*oddušek*) in the NE corner.
* **The Ceiling Bypass:** To avoid the two 90-degree bends upstairs, cut a drywall access hole in the utility room ceiling directly below the vent shaft.
* **The Horizontal Run:** Push a 32mm ribbed conduit (*rebrasta cev*) horizontally through the 4-5cm installation gap (*inštalacijska ravnina*) **below** the plastic vapor barrier, bypassing the wooden slats.
* **The Vertical Drop:** Drop the conduit straight down inside the interior wall cavity to where the inverter will hang.
* **The Seal:** Where the conduit pushes up through the plastic membrane into the vent shaft, meticulously seal it with professional airtight tape (Siga Sicrall, Tyvek, or Gerband).
* **Site Visit Action:** Show Jaka the pre-drywall photo. Point to the ceiling and explain this exact route so his roofers know where to drop the cables.

## 2. The Electrical Panel & Backup Gateway
*Goal: Safely separate Critical and Smart loads for the Sigen Gateway HomePro.*
* **The Schneider Box:** Ask the electrician to open the 30-space Schneider box. *"Do we have enough physical room on the busbar to separate the critical vs. non-critical loads here?"*
* **The New AC/DC Cabinet:** If the Schneider is too full, instruct them to install the new AC/DC cabinet flush-mounted (*podometno*) directly next to the Schneider box on the same interior wall.
* **The EV Relocation:** Ensure the existing carport wire is moved out of the main block and wired directly into the Gateway's "Smart Port" (non-critical load) so it shuts off during a winter grid outage.

## 3. The Carport & EV Charger Integration
*Goal: Maximize the Borzen subsidy and set up automated solar charging.*
* **The Pre-run Cable:** Verify the existing wire in the carport facade box is thick enough for 11 kW continuous charging (look for **5G4** or **5G6** on the jacket).
* **Data Connection:** Point out the pre-run hardwired Ethernet cable in the same box for zero-latency Home Assistant integration.
* **The DC Roof Cabling:** Ask Jaka how they plan to route the DC solar cables from the 12 carport panels back into the house (can they share the existing underground conduit, or do they need a new path?).
* **Site Visit Action:** *"Please add the 11 kW Sigen EV AC Charger to my official quote so we can use the remaining 850 € of my 40% Borzen subsidy allowance."*

## 4. The GEN-I Negotiation Strategy (The Poker Face)
*Goal: Validate JB Energija's math and gain maximum leverage.*
* **The Setup:** Do not offer your 15-minute Moj Elektro data immediately.
* **The Test:** Tell them you have a Mitsubishi Ecodan heat pump and let their engineer calculate your winter Blok 1 needs. See if they try to sell you an undersized 6.9 kWh battery or if they realize you need 15+ kWh.
* **The Reveal:** Once they give you their "best price" for a large system, drop the 12.540 € JB Energija quote on the table and see if they can match the hardware specs and the price.

## 5. Pro-Level System Quirks & Protections
*Goal: Avoid long-term headaches, noise, and hidden grid fees.*
* **Acoustic Placement:** Double-check the exact wall where the 18 kWh SigenStor tower will sit. Ensure it does not share a wall with a bed/headboard, as the high-frequency coil whine and AC hum will be noticeable during heavy winter loads.
* **Carport Snow Cascade:** Look at the main roof above the carport. Ask Jaka: *"Will the main roof shed snow directly onto these carport panels? Do the panels have high-quality bypass diodes for partial snow cover, or do we need optimizers just for the carport string?"*
* **LFP Winter Calibration (Omrežnina Protection):** Remind yourself (or ask the installer) to set a strict **Maximum Grid Charge Rate (e.g., 2 kW or 3 kW)** in the *mySigen* app. This ensures that if the battery forces a 100% calibration cycle during a winter night (Blok 1), it won't pull a 10 kW spike and trigger a massive penalty.
* **Insurance (Post-Install):** The exact day the system is commissioned, call your insurance agent to officially add the *sončna elektrarna* and *hranilnik* to your home policy (hail, lightning, fire).
