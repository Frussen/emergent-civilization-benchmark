from ecb import Action, Direction, RandomPolicy, Simulation, SimulationConfig


class CountingPolicy:
    def __init__(self) -> None:
        self.calls = 0

    def decide(self, observation: object, rng: object) -> Action:
        self.calls += 1
        return Action.move(Direction.EAST)

    def configuration_state(self) -> None:
        return None

    def continuation_state(self) -> int:
        return self.calls


def test_metabolism_deficits_reduce_health_and_death_stops_future_actions() -> None:
    policy = CountingPolicy()
    config = SimulationConfig(
        width=2,
        height=1,
        initial_population=1,
        initial_health=2.0,
        initial_food_inventory=0.0,
        initial_water_inventory=0.0,
        food_regeneration_rate=0.0,
        water_regeneration_rate=0.0,
    )
    simulation = Simulation(config, 0, policy_factory=lambda _id: policy)
    agent = next(iter(simulation.world.agents.values()))
    agent.position = (0, 0)

    simulation.step()
    position_at_death = agent.position
    assert agent.health == 0.0
    assert not agent.alive
    assert policy.calls == 1

    simulation.step({agent.id: Action.move(Direction.EAST)})
    assert agent.position == position_at_death
    assert agent.food_inventory == 0.0
    assert agent.water_inventory == 0.0
    assert policy.calls == 1
    assert simulation.log.metrics[-1].living_population == 0


def test_partial_deficits_apply_additive_penalties() -> None:
    config = SimulationConfig(
        initial_population=1,
        initial_food_inventory=0.25,
        initial_water_inventory=0.5,
        food_need=1.0,
        water_need=1.0,
        food_health_penalty=2.0,
        water_health_penalty=4.0,
    )
    simulation = Simulation(
        config, 0, policy_factory=lambda _id: RandomPolicy()
    )
    agent = next(iter(simulation.world.agents.values()))
    simulation.step({agent.id: Action.wait()})
    assert agent.food_inventory == 0.0
    assert agent.water_inventory == 0.0
    assert agent.health == 96.5
