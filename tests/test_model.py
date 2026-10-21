import math

import pytest

from model import (
    ElectrolysisCell,
    PolarIcePlant,
    current_efficiency,
    propellant_uncertainty_ensemble,
    simulate,
    simulate_hybrid_isru,
    simulate_polar_ice_propellant,
    uncertainty_ensemble,
)


def test_simulation_is_reproducible():
    assert simulate(seed=7) == simulate(seed=7)


def test_mass_is_bounded_by_feedstock():
    result = simulate(hours=300, feedstock_kg=500)
    assert result.processed_regolith_kg + result.unprocessed_regolith_kg == pytest.approx(500)
    assert result.oxygen_kg <= result.processed_regolith_kg
    assert result.metal_product_kg <= result.processed_regolith_kg


def test_wear_reduces_current_efficiency():
    fresh = current_efficiency(0.82, 0, 1600, 1600)
    worn = current_efficiency(0.82, 80, 1600, 1600)
    assert worn < fresh


def test_more_time_does_not_reduce_oxygen_output():
    short = simulate(hours=80, seed=9)
    long = simulate(hours=180, seed=9)
    assert long.oxygen_kg >= short.oxygen_kg


def test_specific_energy_is_finite_after_operation():
    result = simulate(hours=120)
    assert math.isfinite(result.specific_energy_kwh_per_kg_o2)
    assert result.specific_energy_kwh_per_kg_o2 > 0


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        simulate(hours=0)


def test_uncertainty_ensemble_reports_ordered_quantiles():
    out = uncertainty_ensemble(draws=20, hours=90)
    assert out["p10_oxygen_kg"] <= out["mean_oxygen_kg"] <= out["p90_oxygen_kg"]


def test_polar_ice_model_produces_both_fuel_and_oxidizer():
    result = simulate_polar_ice_propellant(hours=300, available_regolith_kg=20_000)
    assert result.recovered_water_kg > 0
    assert result.liquid_hydrogen_kg > 0
    assert result.liquid_oxygen_kg > result.liquid_hydrogen_kg
    assert result.usable_propellant_kg > 0


def test_water_mass_balance_and_engine_ratio_are_explicit():
    plant = PolarIcePlant(engine_oxidizer_fuel_ratio=6.0, hourly_boiloff_fraction=1e-9)
    result = simulate_polar_ice_propellant(hours=100, available_regolith_kg=5_000, plant=plant)
    assert result.liquid_hydrogen_kg + result.liquid_oxygen_kg <= result.recovered_water_kg
    paired_hydrogen = result.usable_propellant_kg / 7
    assert paired_hydrogen <= result.liquid_hydrogen_kg
    assert paired_hydrogen * 6 <= result.liquid_oxygen_kg


def test_propellant_output_respects_power_and_ice_content():
    low = simulate_polar_ice_propellant(hours=200, plant=PolarIcePlant(power_kw=30, ice_mass_fraction=0.02))
    high = simulate_polar_ice_propellant(hours=200, plant=PolarIcePlant(power_kw=90, ice_mass_fraction=0.08))
    assert high.usable_propellant_kg > low.usable_propellant_kg


def test_propellant_uncertainty_reports_ordered_quantiles():
    out = propellant_uncertainty_ensemble(draws=20, hours=120)
    assert out["p10_propellant_kg"] <= out["mean_propellant_kg"] <= out["p90_propellant_kg"]


def test_hybrid_pathway_produces_fuel_oxygen_and_metals():
    result = simulate_hybrid_isru(hours=300)
    assert result.liquid_hydrogen_kg > 0
    assert result.total_stored_oxygen_kg > 0
    assert result.metal_product_kg > 0
    assert result.usable_propellant_kg > 0
    assert result.limiting_propellant == "hydrogen"


def test_molten_pathway_adds_oxygen_but_not_hydrogen():
    result = simulate_hybrid_isru(hours=180)
    assert result.total_stored_oxygen_kg > result.water_pathway.liquid_oxygen_kg
    assert result.liquid_hydrogen_kg == result.water_pathway.liquid_hydrogen_kg
