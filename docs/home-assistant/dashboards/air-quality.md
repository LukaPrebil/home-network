# Air Quality Dashboard

Hidden dashboard showing indoor and outdoor air quality data. Not visible in the sidebar — only reachable via notification deep links from air quality alerts.

## Dashboard

| Property | Value |
|----------|-------|
| URL path | `/air-quality` |
| Title | Kakovost zraka |
| Icon | `mdi:air-filter` |
| Sidebar | Hidden |
| View type | Sections |

## Sections

### Notranja kakovost zraka (Indoor)

Data from the IKEA ALPSTUGA air quality monitor (Matter, living room area).

| Entity | Display name |
|--------|-------------|
| `sensor.alpstuga_air_quality_monitor_air_quality` | Kvaliteta zraka |
| `sensor.alpstuga_air_quality_monitor_carbon_dioxide` | CO2 |
| `sensor.alpstuga_air_quality_monitor_pm2_5` | PM2.5 |
| `sensor.alpstuga_air_quality_monitor_temperature` | Temperatura |
| `sensor.alpstuga_air_quality_monitor_humidity` | Vlaga |

### Zunanja kakovost zraka (Outdoor)

Data from ARSO (Slovenian Environment Agency) air quality monitoring stations.

| Entity | Display name |
|--------|-------------|
| `sensor.arso_kakovost_zraka_eaqi_kranj` | EAQI Kranj |
| `sensor.arso_kakovost_zraka_kranj_pm10` | PM10 Kranj |
| `sensor.arso_kakovost_zraka_kranj_pm2_5` | PM2.5 Kranj |
| `sensor.arso_kakovost_zraka_eaqi_ljubljana_bezigrad` | EAQI Ljubljana |

### Zgodovina (History)

Two 24-hour charts using `apexcharts-card` (HACS) with reference lines:

1. **Indoor** (dual y-axis): CO2 (left axis, reference line at 700 ppm) + PM2.5 (right axis, reference line at 15 µg/m³)
2. **Outdoor** (single y-axis): PM2.5 + PM10 from ARSO Kranj (reference line at 15 µg/m³)

## Usage

This dashboard is the deep link target for air quality notification taps (`url: /air-quality` in notification data). When a user receives a poor air quality alert and taps it, they land here to see current readings and trends.
