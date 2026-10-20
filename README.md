# Energy Hub for Home Assistant

Energy Hub combines the energy sensors you already have into cost, carbon and
efficiency figures, independent of which vendor integrations provide them.
You map your own entities to named slots in a short config flow; everything
else is derived.

It was built on a home with a 1KOMMA5° system (grid meter, PV, battery,
dynamic tariff), a Viessmann gas boiler with solar thermal via ViCare, and
Electricity Maps for carbon intensity. None of that is hard-coded: any
integration that exposes the same kinds of sensors works.

## What you get

- Live powers split by direction: grid import and export, battery charge and
  discharge, household load (computed if you have no sensor for it).
- Cost: import cost, export revenue, gas cost and totals, computed from price
  times energy, or taken from provider cost sensors if you map them.
- Dynamic tariff savings against a flat reference price you enter.
- Carbon: grid import CO2, CO2 avoided by solar, gas combustion CO2, CO2
  avoided by solar thermal, and the live carbon intensity of what your home
  actually consumes.
- Gas in kWh from m³ counters, split by space heating and hot water, with gas
  per heating degree day for weather-normalised comparisons.
- Solar thermal: share of hot water covered by the collector, gas and cost
  avoided.
- Self-sufficiency and self-consumption rate for today.
- A normalised price forecast with today's and tomorrow's min, mean, max and
  cheapest slot, plus a "cheap electricity" binary sensor.
- "Today" counters for all of the above, resetting at local midnight, so stock
  dashboard cards can show daily figures without extra helpers.

Lifetime counters are `total_increasing`, so the Energy Dashboard and the
statistics cards can produce weekly, monthly and yearly views from them.

## Installation

1. In HACS, open **Integrations**, use the three-dots menu and choose
   **Custom repositories**. Add `https://github.com/Jonathan-Sattler/ha-energy-hub`
   as type *Integration*.
2. Install **Energy Hub** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and pick
   **Energy Hub**.

Manual installation: copy `custom_components/energy_hub` into your `config/custom_components`
folder and restart.

## Configuration

The config flow has four steps. Only grid import and grid export energy
counters are required; everything else switches features on when mapped.

| Step | Slots |
|---|---|
| Electricity | grid energy counters, grid power (signed, or import/export pair), solar power and energy, battery power, state of charge, charge and discharge counters, household power and energy |
| Prices | current import price (with optional forecast attribute), export price or fixed feed-in rate, provider cost overrides, flat reference price, provider "cheap" flag |
| Gas and thermal | gas counters for heating, hot water or total (m³ or kWh), calorific value, correction factor, gas price, boiler efficiency, solar thermal counter, temperatures, pump and burner state, outside temperature |
| Carbon | grid CO2 intensity, fossil share, gas emission factor |

Options can be changed later from the integration's **Configure** button; the
integration reloads and keeps its accumulated totals.

### Sign conventions

Signed power sensors differ between vendors. Choose the convention in the
flow:

- Grid power: *negative means export* (default) or *positive means export*.
- Battery power: *positive means charging* (default) or *positive means discharging*.

### Units

Power is accepted in W, kW and MW; energy in Wh, kWh and MWh; gas in m³, ft³
or directly in kWh; temperature in °C, °F or K. Currency comes from your
Home Assistant settings.

### Example mapping

The author's installation, for orientation. `mysite` stands for the
1KOMMA5° site name and `boiler` for the ViCare device name, both of which
Home Assistant uses as entity id prefixes:

| Slot | Entity |
|---|---|
| Grid power (signed, negative is export) | `sensor.mysite_grid_power` |
| Grid import / export energy | `sensor.mysite_grid_consumption_power_energy`, `sensor.mysite_grid_feed_in_power_energy` |
| Solar power / energy | `sensor.mysite_pv_power`, `sensor.mysite_pv_power_energy` |
| Battery power (positive is charging), SoC | `sensor.mysite_battery_power`, `sensor.mysite_battery_soc` |
| Battery charge / discharge energy | `sensor.mysite_battery_charge_power_energy`, `sensor.mysite_battery_discharge_power_energy` |
| Household power / energy | `sensor.mysite_household_power`, `sensor.mysite_household_power_energy` |
| Import price (forecast attribute `forecast`) | `sensor.mysite_current_electricity_price` |
| Cheap flag | `binary_sensor.mysite_cheap_electricity` |
| Gas heating / hot water | `sensor.boiler_heating_gas_consumption_today`, `sensor.boiler_dhw_gas_consumption_today` |
| Solar thermal energy | `sensor.boiler_solar_energy_production_today` |
| Temperatures | `sensor.boiler_solar_collector_temperature`, `…_solar_storage_temperature`, `…_dhw_storage_temperature`, `…_outside_temperature` |
| Grid CO2 intensity, fossil share | `sensor.electricity_maps_co2_intensity`, `sensor.electricity_maps_grid_fossil_fuel_percentage` |

Vendor counters that reset daily are fine: the integration treats a drop as a
reset and keeps counting.

## Dashboard

`dashboards/energy-hub.yaml` is a starter dashboard built only from stock
cards. Create a new empty dashboard, open the raw configuration editor and
paste the file. Replace the entities marked `YOUR ENTITY` with the ones you
mapped. Custom cards with a flow diagram and a price curve are planned.

## Entities

All entities belong to one device named after the hub. Entity ids are
`sensor.energy_hub_<key>`; the keys are listed in
[docs/DATA_MODEL.md](docs/DATA_MODEL.md). A diagnostic sensor *Inactive
features* lists which optional features are off and why, so you can see what
an additional mapping would unlock.

## How totals are computed

Every counter slot is tracked by delta: each time it changes, the difference
is multiplied by the current rate (price, carbon intensity, gas factors) and
added to the matching accumulator. Accumulators and daily windows are
persisted, so restarts do not lose anything. Period comparisons should use
Home Assistant's long-term statistics on the lifetime counters.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
```

## Roadmap

- Per-device consumption list with parent subtraction.
- Slots for solar forecast, EV charger, water meter and heat pump.
- Custom cards: flow diagram, price curve, heating overview, tabbed wrapper.

## License

MIT
