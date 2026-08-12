import copy
import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ANALYSIS_PATH = (
    Path(__file__).resolve().parents[1] / "experiments" / "m0_baseline" / "analyze.py"
)
SPEC = importlib.util.spec_from_file_location("m0_baseline_analyze", ANALYSIS_PATH)
assert SPEC is not None and SPEC.loader is not None
ANALYSIS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ANALYSIS
SPEC.loader.exec_module(ANALYSIS)
AnalysisError = ANALYSIS.AnalysisError
build_summary = ANALYSIS.build_summary
detect_repeating_period = ANALYSIS.detect_repeating_period
load_metrics = ANALYSIS.load_metrics
load_runs = ANALYSIS.load_runs
summary_text = ANALYSIS.summary_text

FIELDNAMES = (
    "tick",
    "alive_agents",
    "survival_fraction",
    "cumulative_deaths",
    "mean_health_alive",
    "total_alive_agent_food",
    "total_alive_agent_water",
    "total_world_food",
    "total_world_water",
    "world_state_hash",
)


def write_metrics(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def metric_row(
    tick: int,
    *,
    alive: int = 2,
    deaths: int = 0,
    health: float | str = 100.0,
    food: float = 10.0,
    water: float = 10.0,
    world_food: float = 40.0,
    world_water: float = 40.0,
    population: int = 2,
    world_state_hash: str | None = None,
) -> dict[str, object]:
    return {
        "tick": tick,
        "alive_agents": alive,
        "survival_fraction": alive / population,
        "cumulative_deaths": deaths,
        "mean_health_alive": health,
        "total_alive_agent_food": food,
        "total_alive_agent_water": water,
        "total_world_food": world_food,
        "total_world_water": world_water,
        "world_state_hash": world_state_hash or f"world-hash-{tick}",
    }


def write_valid_run_set(root: Path) -> None:
    for policy in ANALYSIS.POLICIES:
        prefix = ANALYSIS.RUN_DIRECTORY_PREFIX[policy]
        for seed in ANALYSIS.SEEDS:
            run_directory = root / f"{prefix}{seed}"
            run_directory.mkdir(parents=True)
            initial_hash = f"initial-{seed}"
            final_hash = f"final-{policy}-{seed}"
            write_metrics(
                run_directory / "metrics.csv",
                [
                    metric_row(
                        0,
                        alive=256,
                        population=256,
                        food=5120.0,
                        water=5120.0,
                        world_state_hash=initial_hash,
                    ),
                    metric_row(
                        1,
                        alive=0,
                        deaths=256,
                        health="",
                        food=0.0,
                        water=0.0,
                        population=256,
                        world_state_hash=final_hash,
                    ),
                ],
            )
            metadata = {
                "seed": seed,
                "requested_ticks": ANALYSIS.REQUESTED_TICKS,
                "actual_ticks_completed": 1,
                "extinct": True,
                "termination_reason": "extinction",
                "policy": copy.deepcopy(ANALYSIS.EXPECTED_POLICY_METADATA[policy]),
                "simulation_configuration": copy.deepcopy(
                    ANALYSIS.BASELINE_SIMULATION_CONFIGURATION
                ),
                "software_version": "test-software-source",
                "initial_world_state_hash": initial_hash,
                "final_world_state_hash": final_hash,
            }
            (run_directory / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )


def mutate_metadata(path: Path, field: str, value: object) -> None:
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata[field] = value
    path.write_text(json.dumps(metadata), encoding="utf-8")


def test_loads_early_terminated_run_and_empty_extinction_health(
    tmp_path: Path,
) -> None:
    path = tmp_path / "metrics.csv"
    write_metrics(
        path,
        [
            metric_row(0),
            metric_row(
                1,
                alive=0,
                deaths=2,
                health="",
                food=0.0,
                water=0.0,
            ),
        ],
    )

    run = load_metrics(path, policy="RandomPolicy", seed=0)

    assert [row.tick for row in run.metrics] == [0, 1]
    assert run.metrics[-1].mean_health_alive is None


def test_empty_health_is_rejected_while_agents_are_alive(tmp_path: Path) -> None:
    path = tmp_path / "metrics.csv"
    write_metrics(path, [metric_row(0, health="")])

    with pytest.raises(AnalysisError, match="empty while agents are alive"):
        load_metrics(path, policy="RandomPolicy", seed=0)


def test_summary_generation_is_deterministic(tmp_path: Path) -> None:
    write_valid_run_set(tmp_path)
    runs = load_runs(tmp_path)

    first = build_summary(runs)
    second = build_summary(runs)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert summary_text(first) == summary_text(second)


def test_accepts_fully_valid_six_run_set_and_preserves_provenance(
    tmp_path: Path,
) -> None:
    write_valid_run_set(tmp_path)

    runs = load_runs(tmp_path)
    summary = build_summary(runs)

    assert [(run.policy, run.seed) for run in runs] == [
        (policy, seed) for policy in ANALYSIS.POLICIES for seed in ANALYSIS.SEEDS
    ]
    assert summary["provenance"] == {
        "experiment_design_identifier": "ECB M0.2 baseline",
        "recorded_software_source_identity": "test-software-source",
        "validated_requested_tick_count": 2000,
        "validated_policy_seed_matrix": {
            "RandomPolicy": [0, 1, 2],
            "OracleSurvivalPolicy": [0, 1, 2],
        },
        "baseline_simulation_configuration": (
            ANALYSIS.BASELINE_SIMULATION_CONFIGURATION
        ),
    }


def test_rejects_wrong_recorded_seed(tmp_path: Path) -> None:
    write_valid_run_set(tmp_path)
    path = tmp_path / "random_seed_0" / "metadata.json"
    mutate_metadata(path, "seed", 7)

    with pytest.raises(
        AnalysisError,
        match=r"random_seed_0/metadata.json.*seed.*expected 0.*recorded 7",
    ):
        load_runs(tmp_path)


def test_rejects_wrong_recorded_policy(tmp_path: Path) -> None:
    write_valid_run_set(tmp_path)
    path = tmp_path / "random_seed_0" / "metadata.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["policy"] = copy.deepcopy(
        ANALYSIS.EXPECTED_POLICY_METADATA["OracleSurvivalPolicy"]
    )
    path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(
        AnalysisError,
        match=r"random_seed_0/metadata.json.*policy identity.*RandomPolicy.*Oracle",
    ):
        load_runs(tmp_path)


def test_rejects_wrong_requested_tick_count(tmp_path: Path) -> None:
    write_valid_run_set(tmp_path)
    path = tmp_path / "random_seed_0" / "metadata.json"
    mutate_metadata(path, "requested_ticks", 1999)

    with pytest.raises(
        AnalysisError,
        match=r"random_seed_0/metadata.json.*requested_ticks.*2000.*1999",
    ):
        load_runs(tmp_path)


def test_rejects_changed_simulation_configuration(tmp_path: Path) -> None:
    write_valid_run_set(tmp_path)
    path = tmp_path / "random_seed_0" / "metadata.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["simulation_configuration"]["width"] = 63
    path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(
        AnalysisError,
        match=r"random_seed_0/metadata.json.*simulation_configuration.*63",
    ):
        load_runs(tmp_path)


def test_rejects_mismatched_software_identity_between_runs(tmp_path: Path) -> None:
    write_valid_run_set(tmp_path)
    path = tmp_path / "oracle_seed_2" / "metadata.json"
    mutate_metadata(path, "software_version", "different-source")

    with pytest.raises(
        AnalysisError,
        match=(
            r"oracle_seed_2/metadata.json.*software_version shared across all six "
            r"runs.*test-software-source.*different-source"
        ),
    ):
        load_runs(tmp_path)


def test_rejects_metadata_tick_inconsistent_with_final_metrics(
    tmp_path: Path,
) -> None:
    write_valid_run_set(tmp_path)
    path = tmp_path / "random_seed_0" / "metadata.json"
    mutate_metadata(path, "actual_ticks_completed", 2)

    with pytest.raises(
        AnalysisError,
        match=(
            r"random_seed_0/metadata.json.*actual_ticks_completed vs final metrics "
            r"tick.*expected 1.*recorded 2"
        ),
    ):
        load_runs(tmp_path)


def test_detects_short_period_after_transient() -> None:
    ticks = list(range(13))
    values = [(99.0,), (31.0,), (7.0,)] + [(2.0,), (-2.0,)] * 5

    candidate = detect_repeating_period(ticks, values, max_period=2, min_repeats=4)

    assert candidate is not None
    assert candidate.period_ticks == 2
    assert candidate.periodic_start_tick == 3
    assert candidate.complete_repeats == 5


def test_periodicity_requires_enough_complete_repeats() -> None:
    candidate = detect_repeating_period(
        list(range(7)),
        [(9.0,), (8.0,), (1.0,), (2.0,), (1.0,), (2.0,), (1.0,)],
        max_period=2,
        min_repeats=4,
    )

    assert candidate is None
