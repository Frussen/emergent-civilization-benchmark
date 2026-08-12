from collections import defaultdict

import pytest

from ecb import Action, RandomPolicy, Simulation, SimulationConfig


class DeclaredStatePolicy:
    def __init__(self, state: object) -> None:
        self.state = state

    def decide(self, observation: object, rng: object) -> Action:
        return Action.wait()

    def configuration_state(self) -> dict[str, str]:
        return {"kind": "declared"}

    def continuation_state(self) -> object:
        return self.state


class DrawPolicy:
    def __init__(self, draws: int) -> None:
        self.draws = draws

    def decide(self, observation: object, rng: object) -> Action:
        for _ in range(self.draws):
            rng.choice((0, 1))  # type: ignore[attr-defined]
        return Action.wait()

    def configuration_state(self) -> int:
        return self.draws

    def continuation_state(self) -> None:
        return None


class StatefulList(list[object]):
    pass


def random_simulation(config: SimulationConfig, seed: int) -> Simulation:
    return Simulation(config, seed, policy_factory=lambda _id: RandomPolicy())


def state_simulation(state: object) -> Simulation:
    return Simulation(
        SimulationConfig(initial_population=1),
        4,
        policy_factory=lambda _id: DeclaredStatePolicy(state),
    )


def test_identical_seed_and_policies_produce_identical_trajectory() -> None:
    config = SimulationConfig(width=8, height=7, initial_population=20)
    first = random_simulation(config, 123)
    second = random_simulation(config, 123)

    first_hashes = []
    second_hashes = []
    for _ in range(100):
        first.step()
        second.step()
        first_hashes.append(first.world_state_hash())
        second_hashes.append(second.world_state_hash())
    assert first_hashes == second_hashes
    assert first.execution_state_hash() == second.execution_state_hash()
    assert first.log.actions == second.log.actions
    assert first.log.events == second.log.events


def test_recorded_actions_replay_to_identical_state_hashes() -> None:
    config = SimulationConfig(width=5, height=4, initial_population=12)
    original = random_simulation(config, 91)
    expected_hashes = []
    for _ in range(60):
        original.step()
        expected_hashes.append(original.world_state_hash())

    actions_by_tick: dict[int, dict[str, object]] = defaultdict(dict)
    for tick, agent_id, action in original.log.actions:
        actions_by_tick[tick][agent_id] = action

    replay = random_simulation(config, 91)
    replay_hashes = []
    for tick in range(60):
        replay.step(actions_by_tick[tick])  # type: ignore[arg-type]
        replay_hashes.append(replay.world_state_hash())
    assert replay_hashes == expected_hashes
    assert replay.execution_state_hash() != original.execution_state_hash()


def test_different_seeds_change_initial_state() -> None:
    config = SimulationConfig(width=10, height=10, initial_population=20)
    assert (
        random_simulation(config, 1).world_state_hash()
        != random_simulation(config, 2).world_state_hash()
    )


def test_execution_hash_includes_future_relevant_configuration() -> None:
    first = random_simulation(
        SimulationConfig(initial_population=1, food_need=1.0), 4
    )
    second = random_simulation(
        SimulationConfig(initial_population=1, food_need=2.0), 4
    )
    assert first.world_state_hash() == second.world_state_hash()
    assert first.execution_state_hash() != second.execution_state_hash()


def test_declared_equivalent_nested_state_has_identical_hash() -> None:
    first = state_simulation(
        {"sequence": [1, (2, 3)], "set": {3, 1, 2}}
    )
    second = state_simulation(
        {"set": {1, 2, 3}, "sequence": [1, (2, 3)]}
    )
    assert first.execution_state_hash() == second.execution_state_hash()


def test_declared_container_types_remain_distinct() -> None:
    assert (
        state_simulation([]).execution_state_hash()
        != state_simulation(()).execution_state_hash()
    )
    assert (
        state_simulation(set()).execution_state_hash()
        != state_simulation(frozenset()).execution_state_hash()
    )


def test_unsupported_declared_policy_state_is_rejected() -> None:
    simulation = state_simulation(object())
    with pytest.raises(TypeError, match="unsupported canonical value"):
        simulation.execution_state_hash()


def test_canonical_state_rejects_container_subclasses() -> None:
    simulation = state_simulation(StatefulList())
    with pytest.raises(TypeError, match="unsupported canonical value"):
        simulation.execution_state_hash()


def test_shared_policy_instance_is_rejected() -> None:
    shared = RandomPolicy()
    with pytest.raises(ValueError, match="distinct policy instance"):
        Simulation(
            SimulationConfig(initial_population=2),
            0,
            policy_factory=lambda _id: shared,
        )


def test_agent_policy_rng_streams_are_independent() -> None:
    config = SimulationConfig(initial_population=2)
    first = Simulation(
        config,
        8,
        policy_factory=lambda agent_id: DrawPolicy(20 if agent_id.endswith("0") else 1),
    )
    second = Simulation(
        config,
        8,
        policy_factory=lambda agent_id: DrawPolicy(0 if agent_id.endswith("0") else 1),
    )
    first.step()
    second.step()
    second_id = "agent-000001"
    assert first.policy_rngs[second_id].state() == second.policy_rngs[second_id].state()


def test_execution_hash_includes_policy_rng_wrapper_seed() -> None:
    first = random_simulation(SimulationConfig(initial_population=1), 8)
    second = random_simulation(SimulationConfig(initial_population=1), 8)
    second.policy_rngs["agent-000000"].seed += 1
    assert first.execution_state_hash() != second.execution_state_hash()


def test_run_log_records_source_and_policy_metadata() -> None:
    config = SimulationConfig(width=2, height=2, initial_population=1)
    simulation = random_simulation(config, 42)
    simulation.step()
    assert simulation.log.seed == 42
    assert simulation.log.configuration == config.as_dict()
    assert simulation.log.software_version.startswith("0.1.0")
    assert simulation.log.initial_agent_ids == ("agent-000000",)
    assert simulation.log.policy_identities == {
        "agent-000000": "ecb.policies.RandomPolicy"
    }
    assert simulation.log.policy_configurations == {"agent-000000": None}
    assert len(simulation.log.actions) == 1
    assert simulation.log.metrics[0].tick == 1
    assert simulation.log.tick == 1
