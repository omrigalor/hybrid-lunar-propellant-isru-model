# Methodology

The cell evolves in hourly steps. Electrical input first raises the cell from
ambient lunar temperature to an illustrative molten-regolith operating
temperature while losing heat to the environment. Once hot, available energy
and current efficiency determine processed batch mass.

Current efficiency is modeled as a transparent function of three states:

1. baseline cell efficiency;
2. accumulated electrode wear; and
3. deviation from the target operating temperature.

Oxygen output equals processed mass times the assumed oxygen fraction and
current efficiency. Metal co-product uses the remaining feed fraction and an
explicit recovery parameter. Wear accumulates with processed mass and triggers
maintenance at a stated threshold. Seeded power variation supports reproducible
uncertainty intervals.
