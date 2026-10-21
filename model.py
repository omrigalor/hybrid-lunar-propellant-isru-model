"""Auditable models for lunar oxygen, metal, and water-derived propellant production."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import random


@dataclass(frozen=True)
class ElectrolysisCell:
    power_kw: float = 24.0
    batch_capacity_kg: float = 8.0
    operating_temperature_c: float = 1600.0
    heat_capacity_kwh_c: float = 0.045
    thermal_loss_kw_c: float = 0.0025
    base_specific_energy_kwh_kg: float = 4.6
    oxygen_mass_fraction: float = 0.42
    metal_recovery_fraction: float = 0.72
    initial_current_efficiency: float = 0.82
    electrode_wear_limit: float = 100.0


@dataclass(frozen=True)
class ElectrolysisResult:
    processed_regolith_kg: float
    oxygen_kg: float
    metal_product_kg: float
    unprocessed_regolith_kg: float
    energy_used_kwh: float
    specific_energy_kwh_per_kg_o2: float
    operating_hours: int
    warmup_hours: int
    maintenance_hours: int
    final_current_efficiency: float
    final_electrode_wear: float


@dataclass(frozen=True)
class PolarIcePlant:
    """End-to-end assumptions for mining icy regolith and storing propellant."""

    power_kw: float = 68.0
    mining_rate_kg_h: float = 74.0
    ice_mass_fraction: float = 0.05
    water_extraction_efficiency: float = 0.75
    purification_yield: float = 0.96
    conversion_fraction: float = 0.97
    extraction_kwh_per_kg_regolith: float = 0.27
    electrolysis_kwh_per_kg_water: float = 5.2
    liquefaction_kwh_per_kg_product: float = 1.4
    storage_retention: float = 0.96
    hourly_boiloff_fraction: float = 0.00002
    engine_oxidizer_fuel_ratio: float = 6.0


@dataclass(frozen=True)
class PropellantResult:
    processed_regolith_kg: float
    recovered_water_kg: float
    liquid_oxygen_kg: float
    liquid_hydrogen_kg: float
    usable_propellant_kg: float
    excess_oxygen_kg: float
    energy_used_kwh: float
    operating_hours: int
    specific_energy_kwh_per_kg_propellant: float


@dataclass(frozen=True)
class HybridISRUResult:
    water_pathway: PropellantResult
    regolith_pathway: ElectrolysisResult
    total_stored_oxygen_kg: float
    liquid_hydrogen_kg: float
    usable_propellant_kg: float
    excess_oxygen_kg: float
    metal_product_kg: float
    total_energy_used_kwh: float
    limiting_propellant: str


def current_efficiency(base: float, wear: float, temperature_c: float,
                       target_c: float) -> float:
    """Efficiency falls with electrode wear and temperature deviation."""
    thermal_penalty = min(0.35, abs(temperature_c - target_c) / 900)
    return max(0.35, base * (1 - 0.0045 * wear) * (1 - thermal_penalty))


def simulate(hours: int = 240, feedstock_kg: float = 1000.0,
             cell: ElectrolysisCell = ElectrolysisCell(), seed: int = 23) -> ElectrolysisResult:
    if hours < 1 or feedstock_kg < 0:
        raise ValueError("hours must be positive and feedstock nonnegative")
    if min(asdict(cell).values()) <= 0:
        raise ValueError("cell parameters must be positive")
    if not 0 < cell.oxygen_mass_fraction < 1 or not 0 < cell.metal_recovery_fraction <= 1:
        raise ValueError("yield fractions must be in (0, 1]")

    rng = random.Random(seed)
    temperature = -20.0
    wear = processed = oxygen = metals = energy = 0.0
    operating = warmup = maintenance = 0

    for _ in range(hours):
        if wear >= cell.electrode_wear_limit:
            maintenance += 1
            wear *= 0.25
            continue

        loss_kw = max(0.0, temperature + 20) * cell.thermal_loss_kw_c
        heating_kw = max(0.0, cell.power_kw - loss_kw)
        if temperature < cell.operating_temperature_c - 15:
            temperature += heating_kw / cell.heat_capacity_kwh_c
            temperature = min(cell.operating_temperature_c, temperature)
            energy += cell.power_kw
            warmup += 1
            continue

        if feedstock_kg - processed <= 1e-12:
            break

        efficiency = current_efficiency(
            cell.initial_current_efficiency, wear, temperature,
            cell.operating_temperature_c,
        )
        power_noise = min(1.0, max(0.75, rng.gauss(0.94, 0.045)))
        available_kwh = max(0.0, cell.power_kw * power_noise - loss_kw)
        specific_energy = cell.base_specific_energy_kwh_kg / efficiency
        batch = min(cell.batch_capacity_kg, feedstock_kg - processed,
                    available_kwh / specific_energy)
        used = batch * specific_energy + loss_kw

        oxygen_yield = batch * cell.oxygen_mass_fraction * efficiency
        metal_yield = batch * (1 - cell.oxygen_mass_fraction) * cell.metal_recovery_fraction
        processed += batch
        oxygen += oxygen_yield
        metals += metal_yield
        energy += used
        operating += 1
        wear += batch * (0.055 + 0.035 * (1 - efficiency))
        temperature -= rng.uniform(0.0, 8.0)

    final_efficiency = current_efficiency(
        cell.initial_current_efficiency, wear, temperature,
        cell.operating_temperature_c,
    )
    return ElectrolysisResult(
        processed_regolith_kg=processed,
        oxygen_kg=oxygen,
        metal_product_kg=metals,
        unprocessed_regolith_kg=max(0.0, feedstock_kg - processed),
        energy_used_kwh=energy,
        specific_energy_kwh_per_kg_o2=energy / oxygen if oxygen else math.inf,
        operating_hours=operating,
        warmup_hours=warmup,
        maintenance_hours=maintenance,
        final_current_efficiency=final_efficiency,
        final_electrode_wear=wear,
    )


def uncertainty_ensemble(draws: int = 200, hours: int = 240,
                         feedstock_kg: float = 1000.0,
                         cell: ElectrolysisCell = ElectrolysisCell(),
                         seed: int = 23) -> dict[str, float]:
    if draws < 10:
        raise ValueError("use at least ten draws")
    values = sorted(simulate(hours, feedstock_kg, cell, seed + i).oxygen_kg
                    for i in range(draws))
    return {
        "mean_oxygen_kg": sum(values) / draws,
        "p10_oxygen_kg": values[int(0.1 * draws)],
        "p90_oxygen_kg": values[min(draws - 1, int(0.9 * draws))],
    }


def simulate_polar_ice_propellant(
    hours: int = 24 * 225,
    available_regolith_kg: float = 398_000.0,
    plant: PolarIcePlant = PolarIcePlant(),
    seed: int = 41,
) -> PropellantResult:
    """Simulate icy-regolith extraction, water electrolysis, and cryogenic storage.

    Water is split at its stoichiometric mass fractions into hydrogen and
    oxygen. Usable bipropellant is then limited by the requested engine O/F
    ratio, making any excess oxygen explicit instead of counting it as fuel.
    """
    if hours < 1 or available_regolith_kg < 0:
        raise ValueError("hours must be positive and available regolith nonnegative")
    if min(asdict(plant).values()) <= 0:
        raise ValueError("plant parameters must be positive")
    for fraction in (
        plant.ice_mass_fraction,
        plant.water_extraction_efficiency,
        plant.purification_yield,
        plant.conversion_fraction,
        plant.storage_retention,
        plant.hourly_boiloff_fraction,
    ):
        if not 0 < fraction <= 1:
            raise ValueError("yield and retention fractions must be in (0, 1]")

    rng = random.Random(seed)
    processed = recovered_water = liquid_o2 = liquid_h2 = energy = 0.0
    operating = 0
    water_per_regolith = (
        plant.ice_mass_fraction
        * plant.water_extraction_efficiency
        * plant.purification_yield
    )
    product_per_water = plant.conversion_fraction * plant.storage_retention
    energy_per_regolith = (
        plant.extraction_kwh_per_kg_regolith
        + water_per_regolith * plant.electrolysis_kwh_per_kg_water
        + water_per_regolith * plant.conversion_fraction
        * plant.liquefaction_kwh_per_kg_product
    )

    for _ in range(hours):
        if processed >= available_regolith_kg - 1e-12:
            break
        liquid_o2 *= 1 - plant.hourly_boiloff_fraction
        liquid_h2 *= 1 - plant.hourly_boiloff_fraction
        power_factor = min(1.0, max(0.65, rng.gauss(0.94, 0.04)))
        hourly_capacity = plant.power_kw * power_factor / energy_per_regolith
        batch = min(
            plant.mining_rate_kg_h,
            hourly_capacity,
            available_regolith_kg - processed,
        )
        water = batch * water_per_regolith
        processed += batch
        recovered_water += water
        liquid_h2 += water * (2 / 18) * product_per_water
        liquid_o2 += water * (16 / 18) * product_per_water
        energy += batch * energy_per_regolith
        operating += 1

    paired_hydrogen = min(liquid_h2, liquid_o2 / plant.engine_oxidizer_fuel_ratio)
    usable = paired_hydrogen * (1 + plant.engine_oxidizer_fuel_ratio)
    excess_o2 = max(0.0, liquid_o2 - paired_hydrogen * plant.engine_oxidizer_fuel_ratio)
    return PropellantResult(
        processed_regolith_kg=processed,
        recovered_water_kg=recovered_water,
        liquid_oxygen_kg=liquid_o2,
        liquid_hydrogen_kg=liquid_h2,
        usable_propellant_kg=usable,
        excess_oxygen_kg=excess_o2,
        energy_used_kwh=energy,
        operating_hours=operating,
        specific_energy_kwh_per_kg_propellant=energy / usable if usable else math.inf,
    )


def propellant_uncertainty_ensemble(
    draws: int = 200,
    hours: int = 24 * 225,
    available_regolith_kg: float = 398_000.0,
    plant: PolarIcePlant = PolarIcePlant(),
    seed: int = 41,
) -> dict[str, float]:
    """Report uncertainty from site ice concentration and extraction yield."""
    if draws < 10:
        raise ValueError("use at least ten draws")
    rng = random.Random(seed)
    values = []
    for draw in range(draws):
        sampled = PolarIcePlant(
            **{
                **asdict(plant),
                "ice_mass_fraction": min(0.12, max(0.005, rng.gauss(plant.ice_mass_fraction, 0.012))),
                "water_extraction_efficiency": min(0.95, max(0.35, rng.gauss(plant.water_extraction_efficiency, 0.08))),
            }
        )
        values.append(
            simulate_polar_ice_propellant(
                hours, available_regolith_kg, sampled, seed + draw
            ).usable_propellant_kg
        )
    values.sort()
    return {
        "mean_propellant_kg": sum(values) / draws,
        "p10_propellant_kg": values[int(0.1 * draws)],
        "p90_propellant_kg": values[min(draws - 1, int(0.9 * draws))],
    }


def simulate_hybrid_isru(
    hours: int = 240,
    icy_regolith_kg: float = 20_000.0,
    dry_regolith_kg: float = 1_000.0,
    water_plant: PolarIcePlant = PolarIcePlant(),
    molten_cell: ElectrolysisCell = ElectrolysisCell(),
    regolith_oxygen_storage_retention: float = 0.92,
    seed: int = 41,
) -> HybridISRUResult:
    """Run parallel water-ice and molten-regolith pathways and close the ledger."""
    if not 0 < regolith_oxygen_storage_retention <= 1:
        raise ValueError("oxygen storage retention must be in (0, 1]")
    water = simulate_polar_ice_propellant(
        hours, icy_regolith_kg, water_plant, seed
    )
    regolith = simulate(hours, dry_regolith_kg, molten_cell, seed + 1)
    total_oxygen = (
        water.liquid_oxygen_kg
        + regolith.oxygen_kg * regolith_oxygen_storage_retention
    )
    paired_hydrogen = min(
        water.liquid_hydrogen_kg,
        total_oxygen / water_plant.engine_oxidizer_fuel_ratio,
    )
    usable = paired_hydrogen * (1 + water_plant.engine_oxidizer_fuel_ratio)
    hydrogen_limited = (
        water.liquid_hydrogen_kg
        <= total_oxygen / water_plant.engine_oxidizer_fuel_ratio
    )
    return HybridISRUResult(
        water_pathway=water,
        regolith_pathway=regolith,
        total_stored_oxygen_kg=total_oxygen,
        liquid_hydrogen_kg=water.liquid_hydrogen_kg,
        usable_propellant_kg=usable,
        excess_oxygen_kg=max(
            0.0,
            total_oxygen
            - paired_hydrogen * water_plant.engine_oxidizer_fuel_ratio,
        ),
        metal_product_kg=regolith.metal_product_kg,
        total_energy_used_kwh=water.energy_used_kwh + regolith.energy_used_kwh,
        limiting_propellant="hydrogen" if hydrogen_limited else "oxygen",
    )


if __name__ == "__main__":
    print(json.dumps(asdict(simulate()), indent=2))
