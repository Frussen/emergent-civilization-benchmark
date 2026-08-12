# Emergent Civilization Benchmark

Emergent Civilization Benchmark (ECB) is an open-source scientific multi-agent
simulation and benchmark for studying emergent social dynamics and long-horizon
autonomous agency.

ECB is experimental research software. Its interfaces, methodology, and results
may change as the project develops, and it should not currently be treated as a
production-ready system.

## Status

Milestone M0 provides a framework-independent deterministic simulation kernel:
a configurable rectangular grid, renewable food and water, fixed-cohort agents,
local observations, movement, harvesting, metabolism, death, seeded policies,
replay hashing, and viability calibration. Later social, learning, integration,
and visualization milestones are intentionally not implemented yet.

## Development setup

ECB requires Python 3.12 or newer. Create and activate a virtual environment,
then install the package and development dependencies:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the test suite and linter with:

```sh
make test
make lint
```
