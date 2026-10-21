# Hybrid Lunar Water-Ice Propellant & Molten-Regolith ISRU Model

An end-to-end lunar resource model with two complementary pathways:

- icy regolith is mined, purified, electrolyzed, liquefied, and stored as liquid hydrogen fuel and liquid oxygen oxidizer;
- dry regolith is melted and electrolyzed to produce supplemental oxygen and metal co-products.

The shared ledger reports what a vehicle can actually use after power limits,
resource uncertainty, storage losses, degradation, and engine mixture ratio.
It prevents gross oxygen output from being mistaken for complete return fuel:
hydrogen from lunar water is usually the limiting propellant.

![Hybrid lunar ISRU architecture](assets/reference.svg)

```bash
python -m pip install -e .
python model.py
pytest -q
```

## The question

How much return propellant, breathable or reserve oxygen, and construction metal
can a dual-pathway lunar plant produce when its real bottlenecks are counted?

The water pathway models ice concentration, extraction and purification yield,
electrolysis, liquefaction, boiloff, and the engine oxidizer-to-fuel ratio. The
molten-regolith pathway models 1,600°C startup, heat loss, conversion efficiency,
electrode wear, maintenance, oxygen yield, and metal recovery. The combined
result identifies whether hydrogen or oxygen limits usable propellant.

## Outputs

- processed icy and dry regolith
- recovered water and stored liquid hydrogen
- water-derived and regolith-derived oxygen
- usable paired propellant and excess oxygen
- metal co-products
- energy use, degradation, maintenance, and operating time
- P10/mean/P90 propellant and oxygen output

## Evidence base

- NASA, *Case Study for Lunar ISRU Systems Utilizing Polar Water*:
  https://ntrs.nasa.gov/citations/20205008303
- NASA, *Technology Assessment for Producing Propellant From Lunar Water*:
  https://ntrs.nasa.gov/citations/20230005189
- NASA TechPort, *Lunar Ice Processing (Ice-TP)*:
  https://techport.nasa.gov/projects/156386
- NASA, *Production of Oxygen from Lunar Regolith Using Molten Oxide Electrolysis*:
  https://ntrs.nasa.gov/citations/20090018064

## Limits

This is a low-order research model, not mission-planning or flight hardware
software. Default recovery, energy, storage, melt, and site values are explicit
assumptions. It omits detailed excavation mechanics, contaminant chemistry,
thermal-vacuum hardware, tanker routing, melt chemistry by mineral phase, and
engine qualification.
