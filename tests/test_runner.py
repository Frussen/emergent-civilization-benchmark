import csv
import json
from pathlib import Path

import pytest

from ecb import OracleSurvivalPolicy, RandomPolicy, Simulation, SimulationConfig
from ecb.runner import collect_metric, load_actions, main, run_experiment


def small_config(**changes: int | float) -> SimulationConfig:
    values: dict[str, int | float] = {
        "width": 3,
        "height": 2,
        "initial_population": 4,
        "observation_radius": 1,
    }
    values.update(changes)
    return SimulationConfig(**values)  # type: ignore[arg-type]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as input_file:
        return list(csv.DictReader(input_file))


def read_jsonl(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file]


def test_identical_runs_have_identical_metrics_and_hash_trajectories(
    tmp_path: Path,
) -> None:
    config = small_config()
    first = run_experiment(
        policy="random", seed=11, ticks=12, output=tmp_path / "first", config=config
    )
    second = run_experiment(
        policy="random", seed=11, ticks=12, output=tmp_path / "second", config=config
    )

    assert first.metrics == second.metrics
    assert (tmp_path / "first" / "metrics.csv").read_bytes() == (
        tmp_path / "second" / "metrics.csv"
    ).read_bytes()


def test_runner_does_not_change_direct_headless_trajectory(tmp_path: Path) -> None:
    config = small_config()
    result = run_experiment(
        policy="random", seed=7, ticks=10, output=tmp_path / "run", config=config
    )
    direct = Simulation(config, 7, policy_factory=lambda _id: RandomPolicy())
    direct_hashes = [direct.world_state_hash()]
    for _ in range(10):
        direct.step()
        direct_hashes.append(direct.world_state_hash())

    assert [metric.world_state_hash for metric in result.metrics] == direct_hashes
    assert result.simulation.execution_state_hash() == direct.execution_state_hash()


def test_tick_zero_and_parseable_output_files(tmp_path: Path) -> None:
    output = tmp_path / "run"
    run_experiment(
        policy="random", seed=0, ticks=2, output=output, config=small_config()
    )

    assert {path.name for path in output.iterdir()} == {
        "metadata.json",
        "metrics.csv",
        "events.jsonl",
        "actions.jsonl",
    }
    metadata = json.loads((output / "metadata.json").read_text())
    metrics = read_csv(output / "metrics.csv")
    events = read_jsonl(output / "events.jsonl")
    actions = read_jsonl(output / "actions.jsonl")
    assert metrics[0]["tick"] == "0"
    assert "total_alive_agent_food" in metrics[0]
    assert "total_alive_agent_water" in metrics[0]
    assert "total_agent_food" not in metrics[0]
    assert "total_agent_water" not in metrics[0]
    assert len(metrics) == 3
    assert metadata["actual_ticks_completed"] == 2
    assert isinstance(events, list)
    assert actions


@pytest.mark.parametrize(
    ("name", "policy_type"),
    [("random", RandomPolicy), ("oracle", OracleSurvivalPolicy)],
)
def test_policies_can_be_selected_explicitly(
    tmp_path: Path, name: str, policy_type: type[object]
) -> None:
    result = run_experiment(
        policy=name, seed=0, ticks=1, output=tmp_path / name, config=small_config()
    )
    assert all(
        isinstance(policy, policy_type)
        for policy in result.simulation.policies.values()
    )


def test_invalid_policy_names_fail_clearly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(ValueError, match="unknown policy 'invalid'"):
        run_experiment(
            policy="invalid", seed=0, ticks=1, output=tmp_path / "invalid"
        )
    with pytest.raises(SystemExit):
        main(
            [
                "--policy",
                "invalid",
                "--seed",
                "0",
                "--ticks",
                "1",
                "--output",
                str(tmp_path / "cli-invalid"),
            ]
        )
    assert "invalid choice" in capsys.readouterr().err


def test_extinction_is_recorded_and_terminates_early(tmp_path: Path) -> None:
    config = small_config(
        initial_health=2.0,
        initial_food_inventory=0.0,
        initial_water_inventory=0.0,
        food_initial_stock=0.0,
        water_initial_stock=0.0,
        food_regeneration_rate=0.0,
        water_regeneration_rate=0.0,
    )
    output = tmp_path / "extinction"
    run_experiment(
        policy="random", seed=3, ticks=10, output=output, config=config
    )

    metadata = json.loads((output / "metadata.json").read_text())
    metrics = read_csv(output / "metrics.csv")
    assert metadata["extinct"] is True
    assert metadata["termination_reason"] == "extinction"
    assert metadata["actual_ticks_completed"] == 1
    assert [row["tick"] for row in metrics] == ["0", "1"]
    assert metrics[-1]["mean_health_alive"] == ""


def test_metric_collection_does_not_consume_rng() -> None:
    simulation = Simulation(
        small_config(), 5, policy_factory=lambda _id: RandomPolicy()
    )
    before = (
        simulation._initialization_rng.state(),
        simulation._resolution_rng.state(),
        {key: rng.state() for key, rng in simulation.policy_rngs.items()},
    )
    collect_metric(simulation)
    after = (
        simulation._initialization_rng.state(),
        simulation._resolution_rng.state(),
        {key: rng.state() for key, rng in simulation.policy_rngs.items()},
    )
    assert after == before


def test_inventory_metrics_explicitly_include_only_living_agents() -> None:
    simulation = Simulation(
        small_config(initial_population=2),
        5,
        policy_factory=lambda _id: RandomPolicy(),
        agent_ids=("alive", "dead"),
    )
    simulation.world.agents["alive"].food_inventory = 3.0
    simulation.world.agents["alive"].water_inventory = 4.0
    simulation.world.agents["dead"].health = 0.0
    simulation.world.agents["dead"].food_inventory = 70.0
    simulation.world.agents["dead"].water_inventory = 80.0

    metric = collect_metric(simulation)

    assert metric.total_alive_agent_food == 3.0
    assert metric.total_alive_agent_water == 4.0


def test_action_log_replays_world_hash_trajectory(tmp_path: Path) -> None:
    config = small_config()
    output = tmp_path / "original"
    original = run_experiment(
        policy="random", seed=19, ticks=15, output=output, config=config
    )
    actions_by_tick = load_actions(output / "actions.jsonl")
    replay = Simulation(config, 19, policy_factory=lambda _id: RandomPolicy())
    replay_hashes = [replay.world_state_hash()]
    for tick in range(15):
        replay.step(actions_by_tick[tick])
        replay_hashes.append(replay.world_state_hash())

    assert replay_hashes == [metric.world_state_hash for metric in original.metrics]
