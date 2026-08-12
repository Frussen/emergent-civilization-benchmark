"""Observational analysis of the six recorded ECB M0 baseline runs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

POLICIES = ("RandomPolicy", "OracleSurvivalPolicy")
SEEDS = (0, 1, 2)
EXPERIMENT_DESIGN_IDENTIFIER = "ECB M0.2 baseline"
REQUESTED_TICKS = 2000
RUN_DIRECTORY_PREFIX = {
    "RandomPolicy": "random_seed_",
    "OracleSurvivalPolicy": "oracle_seed_",
}
EXPECTED_POLICY_METADATA = {
    "RandomPolicy": {
        "name": "random",
        "identity": "ecb.policies.RandomPolicy",
        "configuration": None,
    },
    "OracleSurvivalPolicy": {
        "name": "oracle",
        "identity": "ecb.policies.OracleSurvivalPolicy",
        "configuration": {
            "food_need": 1.0,
            "water_need": 1.0,
            "base_harvest_amount": 1.0,
        },
    },
}
BASELINE_SIMULATION_CONFIGURATION = {
    "width": 64,
    "height": 64,
    "initial_population": 256,
    "food_capacity": 20.0,
    "food_initial_stock": 20.0,
    "food_regeneration_rate": 1.0,
    "water_capacity": 20.0,
    "water_initial_stock": 20.0,
    "water_regeneration_rate": 1.0,
    "initial_health": 100.0,
    "initial_food_inventory": 20.0,
    "initial_water_inventory": 20.0,
    "food_need": 1.0,
    "water_need": 1.0,
    "food_health_penalty": 1.0,
    "water_health_penalty": 1.0,
    "base_harvest_amount": 1.0,
    "food_productivity": 2.0,
    "water_productivity": 2.0,
    "observation_radius": 3,
}
REQUIRED_COLUMNS = frozenset(
    {
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
    }
)
PLOT_SPECS = (
    ("alive_agents", "Alive agents", "alive_agents.png"),
    (
        "mean_health_alive",
        "Mean health of living agents",
        "mean_health_alive.png",
    ),
    (
        "total_alive_agent_food",
        "Total alive-agent food inventory",
        "alive_agent_food.png",
    ),
    (
        "total_alive_agent_water",
        "Total alive-agent water inventory",
        "alive_agent_water.png",
    ),
    ("total_world_food", "Total world food", "world_food.png"),
    ("total_world_water", "Total world water", "world_water.png"),
)


class AnalysisError(RuntimeError):
    """Raised when recorded experiment data cannot be analyzed safely."""


@dataclass(frozen=True, slots=True)
class MetricRow:
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
class RunProvenance:
    policy: str
    seed: int
    requested_ticks: int
    actual_ticks_completed: int
    extinct: bool
    termination_reason: str
    simulation_configuration: dict[str, Any]
    software_source_identity: str
    initial_world_state_hash: str
    final_world_state_hash: str


@dataclass(frozen=True, slots=True)
class RunTrajectory:
    policy: str
    seed: int
    source: Path
    metrics: tuple[MetricRow, ...]
    provenance: RunProvenance | None = None


@dataclass(frozen=True, slots=True)
class PeriodCandidate:
    period_ticks: int
    periodic_start_tick: int
    repeated_ticks: int
    complete_repeats: int


def _parse_int(value: str | None, column: str, path: Path, line: int) -> int:
    try:
        if value is None or value.strip() == "":
            raise ValueError
        parsed = int(value)
    except ValueError as error:
        raise AnalysisError(
            f"{path}:{line}: invalid integer in {column!r}: {value!r}"
        ) from error
    return parsed


def _parse_float(value: str | None, column: str, path: Path, line: int) -> float:
    try:
        if value is None or value.strip() == "":
            raise ValueError
        parsed = float(value)
    except ValueError as error:
        raise AnalysisError(
            f"{path}:{line}: invalid number in {column!r}: {value!r}"
        ) from error
    if not math.isfinite(parsed):
        raise AnalysisError(
            f"{path}:{line}: non-finite number in {column!r}: {value!r}"
        )
    return parsed


def _parse_text(value: str | None, column: str, path: Path, line: int) -> str:
    if value is None or value.strip() == "":
        raise AnalysisError(f"{path}:{line}: empty value in {column!r}")
    return value


def _provenance_mismatch(
    path: Path, field: str, expected: object, recorded: object
) -> AnalysisError:
    return AnalysisError(
        f"{path}: provenance mismatch for {field}: "
        f"expected {expected!r}, recorded {recorded!r}"
    )


def _same_json_value(left: object, right: object) -> bool:
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(
        right, sort_keys=True, separators=(",", ":")
    )


def _load_metadata(
    path: Path, *, expected_policy: str, expected_seed: int
) -> RunProvenance:
    if not path.is_file():
        raise AnalysisError(f"required metadata file is missing: {path}")
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AnalysisError(f"could not parse {path}: {error}") from error
    if not isinstance(metadata, dict):
        raise AnalysisError(f"{path}: metadata root must be a JSON object")

    recorded_policy = metadata.get("policy")
    identity = (
        recorded_policy.get("identity") if isinstance(recorded_policy, dict) else None
    )
    policy_by_identity = {
        value["identity"]: policy for policy, value in EXPECTED_POLICY_METADATA.items()
    }
    policy = policy_by_identity.get(identity)
    if policy != expected_policy:
        raise _provenance_mismatch(
            path,
            "policy identity",
            EXPECTED_POLICY_METADATA[expected_policy]["identity"],
            identity,
        )
    expected_policy_metadata = EXPECTED_POLICY_METADATA[policy]
    if not _same_json_value(recorded_policy, expected_policy_metadata):
        raise _provenance_mismatch(
            path, "policy", expected_policy_metadata, recorded_policy
        )

    seed = metadata.get("seed")
    if type(seed) is not int or seed != expected_seed:
        raise _provenance_mismatch(path, "seed", expected_seed, seed)
    requested_ticks = metadata.get("requested_ticks")
    if type(requested_ticks) is not int or requested_ticks != REQUESTED_TICKS:
        raise _provenance_mismatch(
            path, "requested_ticks", REQUESTED_TICKS, requested_ticks
        )
    configuration = metadata.get("simulation_configuration")
    if not _same_json_value(configuration, BASELINE_SIMULATION_CONFIGURATION):
        raise _provenance_mismatch(
            path,
            "simulation_configuration",
            BASELINE_SIMULATION_CONFIGURATION,
            configuration,
        )

    software_identity = metadata.get("software_version")
    if not isinstance(software_identity, str) or not software_identity:
        raise _provenance_mismatch(
            path, "software_version", "a non-empty string", software_identity
        )
    actual_ticks = metadata.get("actual_ticks_completed")
    if type(actual_ticks) is not int or not 0 <= actual_ticks <= requested_ticks:
        raise _provenance_mismatch(
            path,
            "actual_ticks_completed",
            f"an integer from 0 through {requested_ticks}",
            actual_ticks,
        )
    extinct = metadata.get("extinct")
    if type(extinct) is not bool:
        raise _provenance_mismatch(path, "extinct", "a boolean", extinct)
    termination_reason = metadata.get("termination_reason")
    if not isinstance(termination_reason, str):
        raise _provenance_mismatch(
            path, "termination_reason", "a string", termination_reason
        )
    initial_hash = metadata.get("initial_world_state_hash")
    if not isinstance(initial_hash, str) or not initial_hash:
        raise _provenance_mismatch(
            path, "initial_world_state_hash", "a non-empty string", initial_hash
        )
    final_hash = metadata.get("final_world_state_hash")
    if not isinstance(final_hash, str) or not final_hash:
        raise _provenance_mismatch(
            path, "final_world_state_hash", "a non-empty string", final_hash
        )
    return RunProvenance(
        policy=policy,
        seed=seed,
        requested_ticks=requested_ticks,
        actual_ticks_completed=actual_ticks,
        extinct=extinct,
        termination_reason=termination_reason,
        simulation_configuration=dict(configuration),
        software_source_identity=software_identity,
        initial_world_state_hash=initial_hash,
        final_world_state_hash=final_hash,
    )


def load_metrics(path: str | Path, *, policy: str, seed: int) -> RunTrajectory:
    """Load and validate one runner metrics file without changing it."""
    metrics_path = Path(path)
    if not metrics_path.is_file():
        raise AnalysisError(f"required metrics file is missing: {metrics_path}")

    rows: list[MetricRow] = []
    try:
        with metrics_path.open(encoding="utf-8", newline="") as input_file:
            reader = csv.DictReader(input_file, strict=True)
            columns = set(reader.fieldnames or ())
            missing = sorted(REQUIRED_COLUMNS - columns)
            if missing:
                raise AnalysisError(
                    f"{metrics_path}: missing required CSV columns: "
                    + ", ".join(missing)
                )
            for line, record in enumerate(reader, start=2):
                alive_agents = _parse_int(
                    record["alive_agents"], "alive_agents", metrics_path, line
                )
                health_text = record["mean_health_alive"]
                mean_health = (
                    None
                    if health_text is not None and health_text.strip() == ""
                    else _parse_float(
                        health_text, "mean_health_alive", metrics_path, line
                    )
                )
                if alive_agents > 0 and mean_health is None:
                    raise AnalysisError(
                        f"{metrics_path}:{line}: mean_health_alive is empty "
                        "while agents are alive"
                    )
                if alive_agents == 0 and mean_health is not None:
                    raise AnalysisError(
                        f"{metrics_path}:{line}: mean_health_alive must be empty "
                        "when no agents are alive"
                    )
                rows.append(
                    MetricRow(
                        tick=_parse_int(record["tick"], "tick", metrics_path, line),
                        alive_agents=alive_agents,
                        survival_fraction=_parse_float(
                            record["survival_fraction"],
                            "survival_fraction",
                            metrics_path,
                            line,
                        ),
                        cumulative_deaths=_parse_int(
                            record["cumulative_deaths"],
                            "cumulative_deaths",
                            metrics_path,
                            line,
                        ),
                        mean_health_alive=mean_health,
                        total_alive_agent_food=_parse_float(
                            record["total_alive_agent_food"],
                            "total_alive_agent_food",
                            metrics_path,
                            line,
                        ),
                        total_alive_agent_water=_parse_float(
                            record["total_alive_agent_water"],
                            "total_alive_agent_water",
                            metrics_path,
                            line,
                        ),
                        total_world_food=_parse_float(
                            record["total_world_food"],
                            "total_world_food",
                            metrics_path,
                            line,
                        ),
                        total_world_water=_parse_float(
                            record["total_world_water"],
                            "total_world_water",
                            metrics_path,
                            line,
                        ),
                        world_state_hash=_parse_text(
                            record["world_state_hash"],
                            "world_state_hash",
                            metrics_path,
                            line,
                        ),
                    )
                )
    except (OSError, UnicodeError, csv.Error) as error:
        raise AnalysisError(f"could not parse {metrics_path}: {error}") from error

    if not rows:
        raise AnalysisError(f"{metrics_path}: metrics CSV contains no data rows")
    for previous, current in zip(rows, rows[1:], strict=False):
        if current.tick != previous.tick + 1:
            raise AnalysisError(
                f"{metrics_path}: ticks must be consecutive; found "
                f"{previous.tick} followed by {current.tick}"
            )
    if rows[0].tick != 0:
        raise AnalysisError(f"{metrics_path}: first recorded tick must be 0")
    return RunTrajectory(policy, seed, metrics_path, tuple(rows))


def _validate_metadata_metrics_consistency(run: RunTrajectory) -> None:
    provenance = run.provenance
    if provenance is None:
        raise AnalysisError(f"{run.source}: run metadata was not loaded")
    metadata_path = run.source.parent / "metadata.json"
    initial = run.metrics[0]
    final = run.metrics[-1]
    if final.tick != provenance.actual_ticks_completed:
        raise _provenance_mismatch(
            metadata_path,
            "actual_ticks_completed vs final metrics tick",
            final.tick,
            provenance.actual_ticks_completed,
        )
    final_extinct = final.alive_agents == 0
    if provenance.extinct != final_extinct:
        raise _provenance_mismatch(
            metadata_path,
            "extinct vs final metrics alive population",
            final_extinct,
            provenance.extinct,
        )
    if not provenance.extinct and final.tick != provenance.requested_ticks:
        raise _provenance_mismatch(
            metadata_path,
            "actual_ticks_completed for a non-extinct run",
            provenance.requested_ticks,
            final.tick,
        )
    expected_reason = (
        "extinction"
        if provenance.extinct and final.tick < provenance.requested_ticks
        else "requested_ticks_completed"
    )
    if provenance.termination_reason != expected_reason:
        raise _provenance_mismatch(
            metadata_path,
            "termination_reason",
            expected_reason,
            provenance.termination_reason,
        )
    initial_population = provenance.simulation_configuration["initial_population"]
    if initial.alive_agents != initial_population or initial.cumulative_deaths != 0:
        raise _provenance_mismatch(
            run.source,
            "tick-0 population state",
            {"alive_agents": initial_population, "cumulative_deaths": 0},
            {
                "alive_agents": initial.alive_agents,
                "cumulative_deaths": initial.cumulative_deaths,
            },
        )
    expected_deaths = initial_population - final.alive_agents
    if final.cumulative_deaths != expected_deaths:
        raise _provenance_mismatch(
            run.source,
            "final cumulative_deaths",
            expected_deaths,
            final.cumulative_deaths,
        )
    expected_survival = final.alive_agents / initial_population
    if not math.isclose(
        final.survival_fraction, expected_survival, rel_tol=0.0, abs_tol=1e-12
    ):
        raise _provenance_mismatch(
            run.source,
            "final survival_fraction",
            expected_survival,
            final.survival_fraction,
        )
    if initial.world_state_hash != provenance.initial_world_state_hash:
        raise _provenance_mismatch(
            metadata_path,
            "initial_world_state_hash vs metrics",
            initial.world_state_hash,
            provenance.initial_world_state_hash,
        )
    if final.world_state_hash != provenance.final_world_state_hash:
        raise _provenance_mismatch(
            metadata_path,
            "final_world_state_hash vs metrics",
            final.world_state_hash,
            provenance.final_world_state_hash,
        )


def load_runs(input_root: str | Path) -> tuple[RunTrajectory, ...]:
    """Load the fixed M0.2 policy-by-seed design."""
    root = Path(input_root)
    if not root.is_dir():
        raise AnalysisError(f"required run root is missing: {root}")
    runs: list[RunTrajectory] = []
    for expected_policy in POLICIES:
        prefix = RUN_DIRECTORY_PREFIX[expected_policy]
        for seed in SEEDS:
            run_directory = root / f"{prefix}{seed}"
            if not run_directory.is_dir():
                raise AnalysisError(
                    f"required run directory is missing: {run_directory}"
                )
            provenance = _load_metadata(
                run_directory / "metadata.json",
                expected_policy=expected_policy,
                expected_seed=seed,
            )
            loaded = load_metrics(
                run_directory / "metrics.csv",
                policy=provenance.policy,
                seed=provenance.seed,
            )
            run = RunTrajectory(
                policy=loaded.policy,
                seed=loaded.seed,
                source=loaded.source,
                metrics=loaded.metrics,
                provenance=provenance,
            )
            _validate_metadata_metrics_consistency(run)
            runs.append(run)

    first_provenance = runs[0].provenance
    assert first_provenance is not None
    common_software_identity = first_provenance.software_source_identity
    for run in runs[1:]:
        assert run.provenance is not None
        recorded_identity = run.provenance.software_source_identity
        if recorded_identity != common_software_identity:
            raise _provenance_mismatch(
                run.source.parent / "metadata.json",
                "software_version shared across all six runs",
                common_software_identity,
                recorded_identity,
            )
    return tuple(runs)


def _values_close(left: Sequence[float], right: Sequence[float]) -> bool:
    return len(left) == len(right) and all(
        math.isclose(a, b, rel_tol=0.0, abs_tol=1e-9)
        for a, b in zip(left, right, strict=True)
    )


def detect_repeating_period(
    ticks: Sequence[int],
    values: Sequence[Sequence[float]],
    *,
    max_period: int = 32,
    min_repeats: int = 4,
) -> PeriodCandidate | None:
    """Find the shortest strongest exact repeating suffix after a transient."""
    if len(ticks) != len(values):
        raise ValueError("ticks and values must have equal lengths")
    if max_period < 1 or min_repeats < 2:
        raise ValueError("max_period must be positive and min_repeats at least two")
    if any(current != previous + 1 for previous, current in zip(ticks, ticks[1:])):
        raise ValueError("ticks must be consecutive")

    candidates: list[PeriodCandidate] = []
    for period in range(1, min(max_period, len(values) - 1) + 1):
        last_mismatch = period - 1
        for index in range(period, len(values)):
            if not _values_close(values[index], values[index - period]):
                last_mismatch = index
        cycle_start = last_mismatch + 1 - period
        repeated_ticks = len(values) - cycle_start
        if cycle_start >= 0 and repeated_ticks >= min_repeats * period:
            candidates.append(
                PeriodCandidate(
                    period_ticks=period,
                    periodic_start_tick=ticks[cycle_start],
                    repeated_ticks=repeated_ticks,
                    complete_repeats=repeated_ticks // period,
                )
            )
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda candidate: (candidate.repeated_ticks, -candidate.period_ticks),
    )


def _run_summary(run: RunTrajectory) -> dict[str, Any]:
    final = run.metrics[-1]
    return {
        "policy": run.policy,
        "seed": run.seed,
        "final_tick": final.tick,
        "final_alive_population": final.alive_agents,
        "survival_fraction": final.survival_fraction,
        "cumulative_deaths": final.cumulative_deaths,
        "extinction_tick": final.tick if final.alive_agents == 0 else None,
        "final_mean_health": final.mean_health_alive,
        "final_alive_agent_food_inventory": final.total_alive_agent_food,
        "final_alive_agent_water_inventory": final.total_alive_agent_water,
        "final_world_food": final.total_world_food,
        "final_world_water": final.total_world_water,
    }


def _aggregate(values: Sequence[int | float]) -> dict[str, int | float]:
    return {
        "mean": fmean(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def _policy_aggregates(
    run_summaries: Sequence[dict[str, Any]],
) -> dict[str, dict[str, dict[str, int | float]]]:
    aggregate_fields = (
        "final_tick",
        "final_alive_population",
        "survival_fraction",
        "cumulative_deaths",
        "extinction_tick",
        "final_mean_health",
        "final_alive_agent_food_inventory",
        "final_alive_agent_water_inventory",
        "final_world_food",
        "final_world_water",
    )
    result = {}
    for policy in POLICIES:
        policy_runs = [run for run in run_summaries if run["policy"] == policy]
        policy_result = {}
        for field in aggregate_fields:
            values = [run[field] for run in policy_runs if run[field] is not None]
            if values:
                policy_result[field] = _aggregate(values)
        result[policy] = policy_result
    return result


def analyze_oracle_synchronization(
    runs: Sequence[RunTrajectory],
) -> dict[str, Any]:
    """Describe periodicity in Oracle aggregate resource-difference trajectories."""
    oracle_runs = [run for run in runs if run.policy == "OracleSurvivalPolicy"]
    per_seed = []
    candidates: list[PeriodCandidate | None] = []
    for run in oracle_runs:
        inventory_difference = [
            row.total_alive_agent_food - row.total_alive_agent_water
            for row in run.metrics
        ]
        world_difference = [
            row.total_world_food - row.total_world_water for row in run.metrics
        ]
        ticks = [row.tick for row in run.metrics]
        paired = list(zip(inventory_difference, world_difference, strict=True))
        candidate = detect_repeating_period(ticks, paired)
        candidates.append(candidate)
        record: dict[str, Any] = {
            "seed": run.seed,
            "inventory_food_minus_water": {
                "initial": inventory_difference[0],
                "final": inventory_difference[-1],
                "minimum": min(inventory_difference),
                "maximum": max(inventory_difference),
            },
            "world_food_minus_water": {
                "initial": world_difference[0],
                "final": world_difference[-1],
                "minimum": min(world_difference),
                "maximum": max(world_difference),
            },
            "periodicity": None,
        }
        if candidate is not None:
            start_index = ticks.index(candidate.periodic_start_tick)
            period = candidate.period_ticks
            record["periodicity"] = {
                "candidate_period_ticks": period,
                "periodic_start_tick": candidate.periodic_start_tick,
                "transient_tick_range": (
                    [ticks[0], candidate.periodic_start_tick - 1]
                    if candidate.periodic_start_tick > ticks[0]
                    else None
                ),
                "repeated_ticks": candidate.repeated_ticks,
                "complete_repeats": candidate.complete_repeats,
                "inventory_difference_cycle": inventory_difference[
                    start_index : start_index + period
                ],
                "world_difference_cycle": world_difference[
                    start_index : start_index + period
                ],
            }
        per_seed.append(record)

    periods = {
        candidate.period_ticks for candidate in candidates if candidate is not None
    }
    consistent = (
        bool(candidates)
        and all(candidate is not None for candidate in candidates)
        and len(periods) == 1
    )
    strongest_period = next(iter(periods)) if consistent else None
    if strongest_period is None:
        conclusion = (
            "The recorded Oracle aggregate difference trajectories do not provide "
            "consistent evidence of a short repeating period across all seeds."
        )
    else:
        conclusion = (
            f"All Oracle seeds exhibit an exact period-{strongest_period} cycle in "
            "the paired aggregate inventory and world-stock differences after the "
            "reported transient. This is consistent with symmetric food/water needs, "
            "initial inventories, productivity and environment together with "
            "deterministic food-first policy tie-breaking; no causal ablation was "
            "performed, and this is not evidence of emergent social behavior."
        )
    return {
        "method": {
            "signals": [
                "total_alive_agent_food - total_alive_agent_water",
                "total_world_food - total_world_water",
            ],
            "candidate_period_range_ticks": [1, 32],
            "minimum_complete_repeats": 4,
            "criterion": (
                "exact paired-signal repetition within absolute tolerance 1e-9 "
                "for the longest repeating suffix; ties prefer the shorter period"
            ),
        },
        "strongest_supported_candidate_period_ticks": strongest_period,
        "consistent_across_seeds": consistent,
        "per_seed": per_seed,
        "interpretation": conclusion,
    }


def _summary_provenance(runs: Sequence[RunTrajectory]) -> dict[str, Any]:
    expected_matrix = {policy: list(SEEDS) for policy in POLICIES}
    recorded_matrix = {
        policy: sorted(run.seed for run in runs if run.policy == policy)
        for policy in POLICIES
    }
    if recorded_matrix != expected_matrix or len(runs) != len(POLICIES) * len(SEEDS):
        raise AnalysisError(
            "validated run matrix is incomplete: "
            f"expected {expected_matrix!r}, recorded {recorded_matrix!r}"
        )
    provenances = [run.provenance for run in runs]
    if any(provenance is None for provenance in provenances):
        raise AnalysisError(
            "cannot summarize runs without validated metadata provenance"
        )
    validated = [provenance for provenance in provenances if provenance is not None]
    software_identities = {
        provenance.software_source_identity for provenance in validated
    }
    if len(software_identities) != 1:
        raise AnalysisError(
            "validated runs do not share one software/source identity: "
            f"recorded {sorted(software_identities)!r}"
        )
    return {
        "experiment_design_identifier": EXPERIMENT_DESIGN_IDENTIFIER,
        "recorded_software_source_identity": next(iter(software_identities)),
        "validated_requested_tick_count": validated[0].requested_ticks,
        "validated_policy_seed_matrix": recorded_matrix,
        "baseline_simulation_configuration": dict(
            validated[0].simulation_configuration
        ),
    }


def build_summary(runs: Sequence[RunTrajectory]) -> dict[str, Any]:
    """Build a deterministic numerical and descriptive summary."""
    run_summaries = [_run_summary(run) for run in runs]
    return {
        "schema_version": 1,
        "provenance": _summary_provenance(runs),
        "runs": run_summaries,
        "policy_aggregates": _policy_aggregates(run_summaries),
        "oracle_synchronization": analyze_oracle_synchronization(runs),
    }


def _format_number(value: int | float | None) -> str:
    if value is None:
        return "not applicable"
    if isinstance(value, int):
        return str(value)
    return format(value, ".12g")


def summary_text(summary: dict[str, Any]) -> str:
    """Render the summary as deterministic, human-readable plain text."""
    provenance = summary["provenance"]
    lines = [
        "ECB M0.2 First Baseline Analysis",
        "",
        "Provenance",
        f"  experiment design identifier: {provenance['experiment_design_identifier']}",
        "  recorded software/source identity: "
        f"{provenance['recorded_software_source_identity']}",
        "  validated requested tick count: "
        f"{provenance['validated_requested_tick_count']}",
        f"  validated policy/seed matrix: {provenance['validated_policy_seed_matrix']}",
        "  complete baseline simulation configuration:",
    ]
    for name, value in sorted(provenance["baseline_simulation_configuration"].items()):
        lines.append(f"    {name}: {_format_number(value)}")
    lines.extend(["", "Run summaries"])
    for run in summary["runs"]:
        lines.extend(
            [
                "",
                f"{run['policy']}, seed {run['seed']}",
                f"  final tick: {_format_number(run['final_tick'])}",
                "  final alive population: "
                f"{_format_number(run['final_alive_population'])}",
                f"  survival fraction: {_format_number(run['survival_fraction'])}",
                f"  cumulative deaths: {_format_number(run['cumulative_deaths'])}",
                f"  extinction tick: {_format_number(run['extinction_tick'])}",
                f"  final mean health: {_format_number(run['final_mean_health'])}",
                "  final alive-agent food inventory: "
                f"{_format_number(run['final_alive_agent_food_inventory'])}",
                "  final alive-agent water inventory: "
                f"{_format_number(run['final_alive_agent_water_inventory'])}",
                f"  final world food: {_format_number(run['final_world_food'])}",
                f"  final world water: {_format_number(run['final_world_water'])}",
            ]
        )

    lines.extend(["", "Policy aggregates (mean, minimum, maximum)"])
    for policy, fields in summary["policy_aggregates"].items():
        lines.extend(["", policy])
        for name, values in fields.items():
            lines.append(
                f"  {name}: {_format_number(values['mean'])}, "
                f"{_format_number(values['minimum'])}, "
                f"{_format_number(values['maximum'])}"
            )

    synchronization = summary["oracle_synchronization"]
    lines.extend(
        [
            "",
            "Oracle synchronization investigation",
            "  strongest supported candidate period: "
            f"{_format_number(synchronization['strongest_supported_candidate_period_ticks'])}",
            "  consistent across seeds: "
            f"{str(synchronization['consistent_across_seeds']).lower()}",
        ]
    )
    for seed_result in synchronization["per_seed"]:
        periodicity = seed_result["periodicity"]
        if periodicity is None:
            lines.append(f"  seed {seed_result['seed']}: no supported short period")
            continue
        lines.append(
            f"  seed {seed_result['seed']}: period "
            f"{periodicity['candidate_period_ticks']} from tick "
            f"{periodicity['periodic_start_tick']}; inventory difference cycle "
            f"{periodicity['inventory_difference_cycle']}; world difference cycle "
            f"{periodicity['world_difference_cycle']}"
        )
    lines.extend(["", synchronization["interpretation"], ""])
    return "\n".join(lines)


def generate_plots(runs: Sequence[RunTrajectory], output: str | Path) -> list[Path]:
    """Generate the six required independent figures using matplotlib."""
    output_directory = Path(output)
    cache_directory = output_directory / ".matplotlib-cache"
    cache_directory.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_directory))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_directory))
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise AnalysisError(
            "matplotlib is required; install the project analysis extra with "
            "`python -m pip install -e '.[analysis]'`"
        ) from error

    colors = {"RandomPolicy": "#d95f02", "OracleSurvivalPolicy": "#1b73b3"}
    line_styles = {0: "-", 1: "--", 2: ":"}
    generated = []
    for field, label, filename in PLOT_SPECS:
        figure, axes = plt.subplots(figsize=(9, 5.25), constrained_layout=True)
        for run in runs:
            ticks = [row.tick for row in run.metrics]
            values = [getattr(row, field) for row in run.metrics]
            axes.plot(
                ticks,
                values,
                color=colors[run.policy],
                linestyle=line_styles[run.seed],
                linewidth=1.6,
                label=f"{run.policy}, seed {run.seed}",
            )
        axes.set(title=f"M0 baseline: {label}", xlabel="Tick", ylabel=label)
        axes.grid(alpha=0.25)
        axes.legend(fontsize="small")
        path = output_directory / filename
        figure.savefig(
            path,
            dpi=150,
            metadata={"Software": "ECB M0.2 observational analysis"},
        )
        plt.close(figure)
        generated.append(path)
    return generated


def write_outputs(
    runs: Sequence[RunTrajectory], output: str | Path
) -> tuple[Path, ...]:
    """Write all reproducible derived artifacts."""
    output_directory = Path(output)
    output_directory.mkdir(parents=True, exist_ok=True)
    summary = build_summary(runs)
    summary_json = output_directory / "summary.json"
    summary_txt = output_directory / "summary.txt"
    summary_json.write_text(
        json.dumps(summary, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    summary_txt.write_text(summary_text(summary), encoding="utf-8", newline="\n")
    plots = generate_plots(runs, output_directory)
    return (summary_json, summary_txt, *plots)


def build_parser() -> argparse.ArgumentParser:
    repository_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Analyze the six existing ECB M0 baseline trajectories."
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=repository_root / "runs" / "m0",
        help="directory containing random_seed_* and oracle_seed_* runs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "generated",
        help="directory for reproducible plots and summaries",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        runs = load_runs(arguments.input_root)
        outputs = write_outputs(runs, arguments.output)
    except AnalysisError as error:
        raise SystemExit(f"analysis failed: {error}") from error
    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
