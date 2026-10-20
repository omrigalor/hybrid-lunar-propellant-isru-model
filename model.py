"""Thermal, electrochemical, and degradation model for lunar regolith electrolysis."""

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


if __name__ == "__main__":
    print(json.dumps(asdict(simulate()), indent=2))
