# Training curriculum

The machine-readable curriculum is `assets/benchmarks/training_curriculum_v80.csv`; the formatted companion is `assets/examples/generic_v80/Technology_Company_Forecasting_v8.0_Training_Curriculum.xlsx`.

The curriculum is organized as development/untouched-holdout pairs; a default round draws two pairs (the two development cases form Group A, the two holdouts form Group B - four companies per round). Dates are proposed starting boundaries. Before research, verify the precise official publication timestamp and move a boundary backward when necessary; never move it forward simply to include a convenient later filing.

Do not expose post-outcome labels to the Forecaster. The curriculum records economic questions, not the later answer. Keep target Actuals outside the forecast workspace until the seal is created.
