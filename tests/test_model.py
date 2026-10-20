import math

import pytest

from model import ElectrolysisCell, current_efficiency, simulate, uncertainty_ensemble


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
