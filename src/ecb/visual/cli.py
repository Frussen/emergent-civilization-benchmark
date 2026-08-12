"""Command-line startup for one local ECB visual session."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from ecb.config import SimulationConfig
from ecb.runner import _policy_factory
from ecb.simulation import Simulation
from ecb.visual.controller import VisualController
from ecb.visual.runtime import VisualRuntime
from ecb.visual.server import DEFAULT_HOST, DEFAULT_PORT, run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecb-visual", description="Run a local ECB M1 visual backend."
    )
    parser.add_argument("--policy", default="oracle", choices=("random", "oracle"))
    parser.add_argument("--seed", default=0, type=int)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    config = SimulationConfig()
    policy_factory, _metadata = _policy_factory(arguments.policy, config)
    simulation = Simulation(config, arguments.seed, policy_factory=policy_factory)
    runtime = VisualRuntime(VisualController(simulation))
    run_server(runtime, host=arguments.host, port=arguments.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
