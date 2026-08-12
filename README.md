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
and M1 now includes its first local live browser window. Visual Mode observes and
controls the same authoritative simulation; it does not implement another world.

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

## Running M0 experiments

Run a reproducible headless experiment with either the random baseline or the
oracle survival control:

```sh
ecb-run --policy random --seed 0 --ticks 2000 --output runs/random_seed_0
ecb-run --policy oracle --seed 0 --ticks 2000 --output runs/oracle_seed_0
```

The equivalent module interface is `python -m ecb.runner` with the same
arguments. Each output directory contains run metadata, per-tick metrics,
chronological events, and the resolved actions needed for physical replay.
Inventory columns `total_alive_agent_food` and `total_alive_agent_water` sum
stored inventory over living agents only.

## Running the first Visual Mode window

Install the optional Python visual dependencies and the browser dependencies:

```sh
python -m pip install -e ".[visual,dev]"
cd visual
npm install
```

Then run the Oracle survival demo with seed 0 in two terminals:

```sh
# Terminal 1, from the repository root
ecb-visual --policy oracle --seed 0

# Terminal 2
cd visual
npm run dev
```

Open `http://127.0.0.1:5173`. The client connects to
`ws://127.0.0.1:8000/ws`. To inspect the random-policy extinction control,
restart Terminal 1 with `ecb-visual --policy random --seed 0`.

The browser exposes only Play, Pause, Step, and wall-clock speed commands. Drag
the world to pan, use the mouse wheel to zoom around the pointer, and double-click
the canvas to fit the complete world again.
