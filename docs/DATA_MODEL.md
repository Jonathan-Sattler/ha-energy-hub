# Energy Hub — Data Model

Scope agreed on 2026-10-20. This document is the single source of truth for what the
integration consumes (slots and options), what it produces (derived entities), and
which view each value feeds. Nothing in here references a specific vendor integration;
the mapping in [Example mapping](#example-mapping) is only an illustration.

## Principles

- **Slots, not sensors.** Users map their own entities to named slots in the config
  flow. Every derived value is computed from slots. A slot is a contract: domain,
  device class, unit class, state class, and sign convention.
- **Everything optional degrades gracefully.** A missing slot hides the metrics and
  views that need it. It never breaks the rest.
- **Provider values can override computed ones.** Where a vendor integration already
  computes something (cost, self-sufficiency), an override slot accepts it; otherwise
  the integration computes it itself.
- **Long-term totals come from Home Assistant statistics.** The integration emits
  `total_increasing` counters with restore-on-restart. Day, week, month and year
  totals, and previous-period comparisons, are read by the cards through the
  `recorder/statistics_during_period` websocket call, not recomputed.
- **Sign conventions are normalised at the slot boundary.** Users declare the sign
  convention of signed power entities; internal math always uses
  *positive = into the house / into the battery*.

## Input slots

Required slots are marked **R**. Unit classes follow Home Assistant's sensor unit
classes; the integration converts between units of the same class.

### Electricity

| Slot | R | Entity contract | Notes |
|---|---|---|---|
| `grid_power` | | power, W, measurement, signed | Alternative to the import/export pair. Sign option: `negative_is_export` (default) or `positive_is_export`. |
| `grid_import_power` | | power, W, measurement, ≥ 0 | Used if `grid_power` is absent. |
| `grid_export_power` | | power, W, measurement, ≥ 0 | |
| `grid_import_energy` | **R** | energy, kWh, total_increasing | Basis for cost and carbon. |
| `grid_export_energy` | **R** | energy, kWh, total_increasing | |
| `pv_power` | | power, W, measurement | |
| `pv_energy` | | energy, kWh, total_increasing | |
| `battery_power` | | power, W, measurement, signed | Sign option: `positive_is_charging` (default) or `positive_is_discharging`. |
| `battery_soc` | | battery, %, measurement | |
| `battery_charge_energy` | | energy, kWh, total_increasing | |
| `battery_discharge_energy` | | energy, kWh, total_increasing | |
| `battery_capacity_kwh` | | number option | Pre-filled from HA energy preferences when present. |
| `load_power` | | power, W, measurement | If absent, computed: `pv + import − export − battery_charge + battery_discharge`. |
| `load_energy` | | energy, kWh, total_increasing | If absent, computed by Riemann integration of `load_power`. |

### Prices and cost

| Slot | R | Entity contract | Notes |
|---|---|---|---|
| `import_price` | | monetary rate, currency/kWh, measurement | Current price. Optional attribute `forecast` as a list of `{start, end, price}` for the price curve. The attribute name and the keys are configurable so other tariff integrations (Tibber, aWATTar, Nordpool, EPEX) fit. |
| `export_price` | | monetary rate, currency/kWh | Feed-in remuneration. Falls back to option `export_price_fixed`. |
| `import_cost_override` | | monetary, currency, total | Provider-computed cost; replaces internal integration if set. |
| `export_revenue_override` | | monetary, currency, total | |
| `flat_reference_price` | | number option, currency/kWh | What the user would pay on a flat tariff; feeds savings analytics. |
| `cheap_now` | | binary_sensor | Provider flag; otherwise computed from the forecast and option `cheap_threshold_percentile`. |

Currency is read from Home Assistant core settings.

### Gas and thermal

| Slot | R | Entity contract | Notes |
|---|---|---|---|
| `gas_heating_volume` | | gas, m³, total_increasing | Space-heating share. |
| `gas_dhw_volume` | | gas, m³, total_increasing | Domestic hot-water share. |
| `gas_total_volume` | | gas, m³, total_increasing | Used alone when the split is unavailable. A gas slot in kWh is accepted too; the conversion is skipped. |
| `gas_calorific_value` | | number option, kWh/m³ | Default 11.0; country default table, editable. |
| `gas_correction_factor` | | number option | Volume correction factor (Zustandszahl), default 0.95. |
| `gas_price` | | number option, currency/kWh | |
| `gas_price_entity` | | monetary rate | Overrides the number when set. |
| `boiler_efficiency` | | number option | Default 0.95 (condensing boiler). Used to convert heat into gas. |
| `solar_thermal_energy` | | energy, kWh, total_increasing | Heat harvested by the collector. |
| `solar_collector_temp` | | temperature | |
| `solar_storage_temp` | | temperature | |
| `dhw_storage_temp` | | temperature | |
| `solar_pump` | | binary_sensor | |
| `boiler_electricity_energy` | | energy, kWh, total_increasing | Also offered as the first device entry. |
| `burner_modulation` | | %, measurement | Display only. |
| `burner_active` | | binary_sensor | |
| `outside_temp` | | temperature | Needed for heating degree days. |
| `hdd_base_temp` | | number option, °C | Default 15 (German heating limit); 18 is the common alternative. |

### Carbon

| Slot | R | Entity contract | Notes |
|---|---|---|---|
| `grid_co2_intensity` | | gCO2eq/kWh, measurement | |
| `grid_fossil_share` | | %, measurement | Display only. |
| `gas_co2_factor` | | number option, kg CO2/kWh | Default 0.201 for natural gas; country default table. |

### Devices

A list of entries, each `{ name, energy_entity, power_entity?, parent? }`. `parent`
names another entry or a slot (`load_energy`, `gas_total_volume`) whose total already
includes this device, so the remainder can be shown as "other".

### Reserved slots (v1 ships the slot, not the view logic)

| Slot | Entity contract |
|---|---|
| `solar_forecast_today`, `solar_forecast_tomorrow` | energy, kWh |
| `ev_charger_power`, `ev_session_energy`, `ev_soc` | power, energy, battery |
| `water_volume`, `water_price` | water m³ total_increasing, option |
| `heatpump_electric_energy`, `heatpump_thermal_energy`, `heatpump_cop` | energy, energy, number |

## Derived entities

All derived energy and monetary counters are `total_increasing` with restore state
unless noted. Rates are `measurement`. Names are the integration's translation keys;
entity ids are `sensor.energy_hub_<key>`.

### Electricity

| Key | Formula | Needs |
|---|---|---|
| `grid_import_power`, `grid_export_power` | split from `grid_power` by sign, or passthrough | grid power slots |
| `battery_charge_power`, `battery_discharge_power` | split from `battery_power` | battery power |
| `load_power` | see slot table | pv, grid, battery |
| `load_energy` | Riemann (trapezoidal) of `load_power` | |
| `pv_self_consumed_energy` | `pv_energy − grid_export_energy + battery_discharge_energy_from_pv` (battery share approximated by charge/discharge counters) | pv, grid, battery |
| `self_sufficiency` (%) | `1 − import / load`, daily window | load, import |
| `self_consumption_rate` (%) | `self_consumed / pv`, daily window | pv, export |

### Cost

| Key | Formula | Needs |
|---|---|---|
| `import_cost` | Σ `import_price × Δimport_energy` per update, or override | price, import energy |
| `export_revenue` | Σ `export_price × Δexport_energy`, or override | export price or fixed |
| `net_electricity_cost` | `import_cost − export_revenue` | |
| `gas_energy_heating`, `gas_energy_dhw`, `gas_energy_total` (kWh) | `m³ × calorific × correction` | gas slots and options |
| `gas_cost` | `gas_energy_total × gas_price` | |
| `total_energy_cost` | `net_electricity_cost + gas_cost` | |
| `flat_tariff_cost` | Σ `flat_reference_price × Δimport_energy` | reference option |
| `dynamic_tariff_savings` | `flat_tariff_cost − import_cost` | |
| `avg_import_price_paid` (currency/kWh, measurement) | `import_cost / import_energy` over the day | |

### Carbon

| Key | Formula | Needs |
|---|---|---|
| `grid_import_co2` (kg) | Σ `intensity × Δimport_energy` | intensity, import |
| `avoided_co2_pv` (kg) | Σ `intensity × Δ(pv_self_consumed + export)` | intensity, pv, export |
| `gas_co2` (kg) | `gas_energy_total × gas_co2_factor` | gas |
| `solar_thermal_avoided_co2` (kg) | `solar_thermal_energy / boiler_efficiency × gas_co2_factor` | solar thermal |
| `total_co2` (kg) | `grid_import_co2 + gas_co2` | |
| `home_co2_intensity` (gCO2/kWh, measurement) | `grid_import_power × intensity / load_power`, 0 for solar and battery share | intensity, powers |

### Thermal

| Key | Formula | Needs |
|---|---|---|
| `dhw_heat_total` (kWh) | `solar_thermal_energy + gas_energy_dhw × boiler_efficiency` | |
| `solar_share_of_dhw` (%) | `solar_thermal_energy / dhw_heat_total`, daily | |
| `solar_thermal_gas_avoided_volume` (m³) | `solar_thermal_energy / boiler_efficiency / (calorific × correction)` | |
| `solar_thermal_gas_avoided_cost` | `… × gas_price` | |
| `heating_degree_days` | daily `max(0, hdd_base_temp − mean(outside_temp))` | outside temp |
| `gas_per_hdd` (kWh/K·d, measurement) | `gas_energy_heating_today / heating_degree_days_today` | |

### Status and diagnostics

| Key | Type | Content |
|---|---|---|
| `flow_state` | sensor (enum) | `importing`, `exporting`, `self_powered`, `charging`, `discharging` summary for the flow card |
| `cheap_electricity` | binary_sensor | passthrough or computed from forecast |
| `price_forecast` | sensor with attribute | normalised `forecast` list in a fixed schema for the price card |
| `missing_slots` | diagnostic sensor | which optional features are inactive and why |

## Views and what feeds them

| View | Card | Values |
|---|---|---|
| Live flow | `energy-hub-flow-card` | all `*_power`, `battery_soc`, `import_price`, `grid_co2_intensity`, `flow_state`, `burner_active`, `burner_modulation`, `solar_pump` |
| Period summary | `energy-hub-summary-card` | statistics for import, export, pv, load, battery, gas kWh, solar thermal, all cost and CO2 counters; `self_sufficiency`, `self_consumption_rate`; previous-period deltas |
| Prices and tariff | `energy-hub-price-card` | `price_forecast`, `import_price`, price min/avg/max, cheap windows, spot and grid-cost breakdown attributes when present, `dynamic_tariff_savings`, provider EMS flags if mapped |
| Heating and thermal | `energy-hub-heating-card` | gas heating vs DHW, `solar_share_of_dhw`, storage and collector temps, `burner_modulation`, `gas_per_hdd`, `heating_degree_days`, outside temperature |
| Wrapper | `energy-hub-card` | tabs over the four cards; visual editor selects tabs |

## Example mapping

The author's installation, used in the README as a worked example:

| Slot | Entity | Note |
|---|---|---|
| `grid_power` | `sensor.mysite_grid_power` | negative is export |
| `grid_import_energy` | `sensor.mysite_grid_consumption_power_energy` | |
| `grid_export_energy` | `sensor.mysite_grid_feed_in_power_energy` | |
| `pv_power`, `pv_energy` | `sensor.mysite_pv_power`, `…_pv_power_energy` | |
| `battery_power` | `sensor.mysite_battery_power` | positive is charging |
| `battery_soc` | `sensor.mysite_battery_soc` | capacity 11.6 kWh |
| `battery_charge_energy`, `battery_discharge_energy` | `…_battery_charge_power_energy`, `…_battery_discharge_power_energy` | |
| `load_power`, `load_energy` | `sensor.mysite_household_power`, `…_household_power_energy` | |
| `import_price` | `sensor.mysite_current_electricity_price` | `forecast` attribute, 15-min slots |
| `import_cost_override` | `sensor.mysite_electricity_cost` | optional |
| `export_revenue_override` | `sensor.mysite_feed_in_revenue` | optional |
| `cheap_now` | `binary_sensor.mysite_cheap_electricity` | |
| `gas_heating_volume` | `sensor.boiler_heating_gas_consumption_today` | the `_2` twin is the second heating circuit |
| `gas_dhw_volume` | `sensor.boiler_dhw_gas_consumption_today` | |
| `solar_thermal_energy` | `sensor.boiler_solar_energy_production_today` | |
| `solar_collector_temp`, `solar_storage_temp`, `dhw_storage_temp` | `sensor.boiler_solar_collector_temperature`, `…_solar_storage_temperature`, `…_dhw_storage_temperature` | |
| `solar_pump`, `burner_active`, `burner_modulation` | `binary_sensor.…_solar_pump`, `binary_sensor.…_burner`, `sensor.…_burner_modulation` | |
| `boiler_electricity_energy` | `sensor.boiler_electricity_consumption_today` | also device entry "Boiler" |
| `outside_temp` | `sensor.boiler_outside_temperature` | |
| `grid_co2_intensity`, `grid_fossil_share` | `sensor.electricity_maps_co2_intensity`, `…_grid_fossil_fuel_percentage` | |

## Project decisions

- Name: integration domain `energy_hub`, repo `ha-energy-hub`, cards `energy-hub-*`.
- Supported Home Assistant: latest release line only.
- Translations: English and German for integration and cards.
- Units: metric only in v1. Currency from Home Assistant.
- Defaults for calorific value, correction factor and emission factors come from a
  per-country table and are editable.
- Period totals are computed from recorder statistics in the cards; the integration
  does not maintain its own daily or monthly counters.

## Open items

- The battery share of self-consumed PV is approximated from counters; a charge-source
  split needs a vendor sensor and is not planned for v1.
- The `forecast` attribute schema varies between tariff integrations. The normaliser
  needs test fixtures for at least Tibber, Nordpool, aWATTar and EPEX in addition to the
  author's provider.
- Daily-resetting vendor counters (the "today" gas and solar-thermal sensors) were
  verified against recorder history on 2026-10-20: they increase monotonically within a
  day, reset to zero at midnight, update roughly every two hours in 0.1 steps, and
  briefly go `unavailable` on API hiccups. Home Assistant statistics sum the daily
  change correctly across the reset. The integration must ignore `unavailable` and
  `unknown` states when computing deltas, and must not treat the coarse two-hour
  cadence as live data in the flow view. Faster polling cannot help: the ViCare
  integration already polls every 60 s and the value only changes on Viessmann's
  two-hourly backend batch. The vendor's weekly, monthly and yearly variants share that
  cadence. Burner modulation is the only minute-resolution signal; a modulation-based
  gas estimate was considered and deferred, the vendor counters stay authoritative.
- The author's boiler also exposes disabled vendor kWh sensors ("Energy", "Heating
  energy consumption this year", "DHW energy consumption this year"). Enabling them
  allows a cross-check of the configured calorific value against Viessmann's own
  assumption.
