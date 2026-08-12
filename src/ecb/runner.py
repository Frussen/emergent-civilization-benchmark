"""Reproducible, headless M0 experiment execution and file output."""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from ecb.config import SimulationConfig
from ecb.model import (
    Action,
    ActionKind,
    DeathEvent,
    Direction,
    HarvestEvent,
    InvalidActionEvent,
    Resource,
    WorldEvent,
)
from ecb.policies import OracleSurvivalPolicy, Policy, RandomPolicy
from ecb.simulation import Simulation


@dataclass(frozen=True, slots=True)
class ExperimentMetric:
    tick: int
    alive_agents: int
    survival_fraction: float
    cumulative_deaths: int
    mean_health_alive: float | None
    total_alive_agent_food: float
    total_alive_agent_water: float
    total_world_food: float
    total_world_water: float
    world_state_hash: str


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    simulation: Simulation
    metrics: tuple[ExperimentMetric, ...]
    output_directory: Path


def _policy_factory(
    policy_name: str, config: SimulationConfig
) -> tuple[Callable[[str], Policy], dict[str, object]]:
    if policy_name == "random":
        return lambda _agent_id: RandomPolicy(), {
            "name": policy_name,
            "identity": "ecb.policies.RandomPolicy",
            "configuration": None,
        }
    if policy_name == "oracle":
        policy_configuration = {
            "food_need": config.food_need,
            "water_need": config.water_need,
            "base_harvest_amount": config.base_harvest_amount,
        }
        return lambda _agent_id: OracleSurvivalPolicy(**policy_configuration), {
            "name": policy_name,
            "identity": "ecb.policies.OracleSurvivalPolicy",
            "configuration": policy_configuration,
        }
    raise ValueError(
        f"unknown policy {policy_name!r}; expected one of: oracle, random"
    )


def collect_metric(simulation: Simulation) -> ExperimentMetric:
    """Observe aggregate state without mutating the simulation or its RNGs."""
    living = simulation.world.living_agents()
    alive_agents = len(living)
    initial_population = simulation.initial_population
    survival_fraction = (
        alive_agents / initial_population if initial_population else 1.0
    )
    mean_health = (
        sum(agent.health for agent in living) / alive_agents
        if alive_agents
        else None
    )
    return ExperimentMetric(
        tick=simulation.world.tick,
        alive_agents=alive_agents,
        survival_fraction=survival_fraction,
        cumulative_deaths=initial_population - alive_agents,
        mean_health_alive=mean_health,
        total_alive_agent_food=sum(agent.food_inventory for agent in living),
        total_alive_agent_water=sum(agent.water_inventory for agent in living),
        total_world_food=sum(
            cell.food.stock for cell in simulation.world.cells.values()
        ),
        total_world_water=sum(
            cell.water.stock for cell in simulation.world.cells.values()
        ),
        world_state_hash=simulation.world_state_hash(),
    )


def run_experiment(
    *,
    policy: str,
    seed: int,
    ticks: int,
    output: str | Path,
    config: SimulationConfig = SimulationConfig(),
) -> ExperimentResult:
    """Run an M0 experiment and write deterministic scientific outputs."""
    if ticks < 0:
        raise ValueError("ticks cannot be negative")
    policy_factory, policy_metadata = _policy_factory(policy, config)
    simulation = Simulation(config, seed, policy_factory=policy_factory)
    initial_world_state_hash = simulation.world_state_hash()
    metrics = [collect_metric(simulation)]

    for _ in range(ticks):
        if not simulation.world.living_agents():
            break
        simulation.step()
        metrics.append(collect_metric(simulation))

    simulation.verify_invariants()
    output_directory = Path(output)
    output_directory.mkdir(parents=True, exist_ok=True)
    _write_metrics(output_directory / "metrics.csv", metrics)
    _write_events(output_directory / "events.jsonl", simulation.log.events)
    _write_actions(output_directory / "actions.jsonl", simulation.log.actions)

    extinct = not simulation.world.living_agents()
    metadata = {
        "seed": seed,
        "requested_ticks": ticks,
        "actual_ticks_completed": simulation.world.tick,
        "extinct": extinct,
        "termination_reason": (
            "extinction"
            if extinct and simulation.world.tick < ticks
            else "requested_ticks_completed"
        ),
        "policy": policy_metadata,
        "simulation_configuration": config.as_dict(),
        "initial_agent_ids": list(simulation.log.initial_agent_ids),
        "software_version": simulation.log.software_version,
        "initial_world_state_hash": initial_world_state_hash,
        "final_world_state_hash": simulation.world_state_hash(),
        "final_execution_state_hash": simulation.execution_state_hash(),
    }
    _write_json(output_directory / "metadata.json", metadata)
    return ExperimentResult(simulation, tuple(metrics), output_directory)


def load_actions(path: str | Path) -> dict[int, dict[str, Action]]:
    """Load a runner action log into maps accepted by ``Simulation.step``."""
    actions: dict[int, dict[str, Action]] = {}
    with Path(path).open(encoding="utf-8") as action_file:
        for line_number, line in enumerate(action_file, start=1):
            record = json.loads(line)
            tick = record["tick"]
            agent_id = record["agent_id"]
            action_data = record["action"]
            action = Action(
                kind=ActionKind(action_data["kind"]),
                direction=(
                    Direction(action_data["direction"])
                    if action_data["direction"] is not None
                    else None
                ),
                resource=(
                    Resource(action_data["resource"])
                    if action_data["resource"] is not None
                    else None
                ),
            )
            tick_actions = actions.setdefault(tick, {})
            if agent_id in tick_actions:
                raise ValueError(
                    f"duplicate action for {agent_id!r} on line {line_number}"
                )
            tick_actions[agent_id] = action
    return actions


def _write_json(path: Path, value: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(value, output_file, allow_nan=False, indent=2, sort_keys=True)
        output_file.write("\n")


def _write_metrics(path: Path, metrics: list[ExperimentMetric]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=list(ExperimentMetric.__dataclass_fields__),
        )
        writer.writeheader()
        writer.writerows(asdict(metric) for metric in metrics)


def _write_actions(
    path: Path, actions: list[tuple[int, str, Action]]
) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        for tick, agent_id, action in actions:
            record = {
                "tick": tick,
                "agent_id": agent_id,
                "action": {
                    "kind": action.kind.value,
                    "direction": (
                        action.direction.value if action.direction is not None else None
                    ),
                    "resource": (
                        action.resource.value if action.resource is not None else None
                    ),
                },
            }
            output_file.write(json.dumps(record, allow_nan=False, sort_keys=True))
            output_file.write("\n")


def _event_record(event: WorldEvent) -> dict[str, object]:
    if isinstance(event, InvalidActionEvent):
        return {
            "event_type": "invalid_action",
            "tick": event.tick,
            "agent_id": event.agent_id,
            "action": {
                "kind": event.action.kind.value,
                "direction": (
                    event.action.direction.value
                    if event.action.direction is not None
                    else None
                ),
                "resource": (
                    event.action.resource.value
                    if event.action.resource is not None
                    else None
                ),
            },
            "reason": event.reason,
        }
    if isinstance(event, HarvestEvent):
        return {
            "event_type": "harvest",
            "tick": event.tick,
            "agent_id": event.agent_id,
            "resource": event.resource.value,
            "amount": event.amount,
            "position": list(event.position),
        }
    if isinstance(event, DeathEvent):
        return {
            "event_type": "death",
            "tick": event.tick,
            "agent_id": event.agent_id,
        }
    raise TypeError(f"unsupported event type: {type(event)!r}")


def _write_events(path: Path, events: list[WorldEvent]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        for event in events:
            output_file.write(
                json.dumps(_event_record(event), allow_nan=False, sort_keys=True)
            )
            output_file.write("\n")


def _nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecb-run", description="Run a reproducible headless ECB M0 experiment."
    )
    parser.add_argument("--policy", required=True, choices=("random", "oracle"))
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--ticks", required=True, type=_nonnegative_int)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    run_experiment(
        policy=arguments.policy,
        seed=arguments.seed,
        ticks=arguments.ticks,
        output=arguments.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
