# M0 Baseline Experiment

This directory documents the first empirical baseline experiment of the **Emergent Civilization Benchmark (ECB)**.

The purpose of this experiment is not to demonstrate emergent social behavior. It is a validation experiment for the M0 simulation kernel: the environment should permit long-term survival when controlled by a sufficiently competent legal policy, while survival should not be guaranteed independently of agent behavior.

---

## 1. Research question

The primary question is:

> Does the M0 baseline environment permit long-term survival while remaining sensitive to agent policy quality?

A useful baseline should satisfy both conditions:

1. survival must be physically achievable;
2. poor decision-making must still be capable of producing failure or extinction.

If every policy survives automatically, the environment provides little selection pressure.

If even a competent policy cannot survive, the environment is ecologically inconsistent for the intended benchmark.

---

## 2. Experimental status

This experiment corresponds to:

**ECB M0.2 — First Baseline Analysis**

It uses the already validated:

* M0 deterministic simulation kernel;
* M0.1 reproducible headless experiment runner.

No new simulation mechanics are introduced by this experiment.

---

## 3. Baseline world configuration

The experiment uses the default M0 configuration defined in `docs/MODEL_SPEC.md`.

### World

* grid width: 64;
* grid height: 64;
* initial population: 256 agents;
* multiple agents may occupy the same cell;
* world boundaries are non-toroidal.

### Resources

Every cell starts with:

* food capacity: 20.0;
* initial food stock: 20.0;
* food regeneration: 1.0 per tick;
* water capacity: 20.0;
* initial water stock: 20.0;
* water regeneration: 1.0 per tick.

The maximum global stock of each resource is therefore:

`64 × 64 × 20 = 81,920`

M0 intentionally uses a spatially homogeneous and resource-abundant environment.

### Agents

Every agent starts with:

* health: 100;
* food inventory: 20.0;
* water inventory: 20.0;
* food productivity: 2.0;
* water productivity: 2.0.

Agents require each tick:

* food: 1.0;
* water: 1.0.

There are:

* no births;
* no reproduction;
* no evolution;
* no trade;
* no social memory;
* no communication;
* no institutions.

---

## 4. Policies

Two M0 policies are compared.

### RandomPolicy

`RandomPolicy` selects uniformly from the complete M0 primitive action set:

* WAIT;
* eight MOVE directions;
* HARVEST food;
* HARVEST water.

It has no survival objective and serves as a weak behavioral control.

### OracleSurvivalPolicy

`OracleSurvivalPolicy` is a test-only survival controller.

Despite its name, it has no privileged access to the world.

It receives the same legal local `Observation` interface as other policies and chooses actions intended to maintain food and water reserves.

It is not considered a benchmark participant and its behavior is not evidence of emergent intelligence.

---

## 5. Experimental design

Each policy was evaluated on three seeds:

* 0;
* 1;
* 2.

Maximum requested duration:

`2,000 ticks`

Runs terminate early if the entire population becomes extinct.

This produces six experimental runs:

| Policy               | Seed | Requested ticks |
| -------------------- | ---: | --------------: |
| RandomPolicy         |    0 |            2000 |
| RandomPolicy         |    1 |            2000 |
| RandomPolicy         |    2 |            2000 |
| OracleSurvivalPolicy |    0 |            2000 |
| OracleSurvivalPolicy |    1 |            2000 |
| OracleSurvivalPolicy |    2 |            2000 |

---

## 6. Commands

The experiments were generated with the M0.1 headless runner.

```bash
ecb-run --policy random --seed 0 --ticks 2000 --output runs/m0/random_seed_0
ecb-run --policy random --seed 1 --ticks 2000 --output runs/m0/random_seed_1
ecb-run --policy random --seed 2 --ticks 2000 --output runs/m0/random_seed_2

ecb-run --policy oracle --seed 0 --ticks 2000 --output runs/m0/oracle_seed_0
ecb-run --policy oracle --seed 1 --ticks 2000 --output runs/m0/oracle_seed_1
ecb-run --policy oracle --seed 2 --ticks 2000 --output runs/m0/oracle_seed_2
```

Raw run outputs are intentionally stored under the ignored `runs/` directory rather than committed to the repository.

Each run contains:

* `metadata.json`;
* `metrics.csv`;
* `events.jsonl`;
* `actions.jsonl`.

---

## 7. Final results

### OracleSurvivalPolicy

| Seed | Final tick | Alive | Survival | Deaths | Mean health | Food inventory | Water inventory | World food | World water |
| ---: | ---------: | ----: | -------: | -----: | ----------: | -------------: | --------------: | ---------: | ----------: |
|    0 |       2000 |   256 |      1.0 |      0 |       100.0 |           5100 |            5100 |      81740 |       81484 |
|    1 |       2000 |   256 |      1.0 |      0 |       100.0 |           5092 |            5092 |      81668 |       81412 |
|    2 |       2000 |   256 |      1.0 |      0 |       100.0 |           5102 |            5102 |      81758 |       81502 |

Across all three seeds:

* survival at tick 2000: 100%;
* deaths: 0;
* mean health at tick 2000: 100;
* mean final food inventory: 5098;
* mean final water inventory: 5098;
* mean final world food: 81,722;
* mean final world water: 81,466.

The final global environment remains close to its maximum resource capacity of 81,920 units per resource.

---

### RandomPolicy

| Seed | Extinction tick | Alive | Survival | Deaths | World food | World water |
| ---: | --------------: | ----: | -------: | -----: | ---------: | ----------: |
|    0 |              99 |     0 |      0.0 |    256 |      81920 |       81920 |
|    1 |              98 |     0 |      0.0 |    256 |      81920 |       81920 |
|    2 |              96 |     0 |      0.0 |    256 |      81920 |       81920 |

Across the three seeds:

* complete extinction occurred in every run;
* extinction tick range: 96–99;
* mean extinction tick: approximately 97.7;
* final food stock: 81,920 in every run;
* final water stock: 81,920 in every run.

The population therefore becomes extinct while the environment itself is fully resource-abundant.

---

## 8. Baseline observation

The first M0 baseline observation is:

> In the M0 baseline, OracleSurvivalPolicy maintained 100% population survival through tick 2,000 across seeds 0–2, whereas RandomPolicy produced complete extinction between ticks 96 and 99 despite environmental resources remaining at or near maximum capacity.

This supports the intended M0 viability property:

> **The environment permits long-term survival, but survival depends strongly on policy quality.**

The RandomPolicy population does not appear to fail because the environment runs out of resources.

Instead, agents fail to perform sufficiently directed resource-acquisition behavior despite living in an abundant environment.

This is an important distinction: ecological survival is possible, but it is not automatically granted by the simulation.

---

## 9. Why RandomPolicy fails

RandomPolicy chooses uniformly among 11 primitive actions:

* 1 WAIT;
* 8 MOVE actions;
* 1 HARVEST food action;
* 1 HARVEST water action.

With baseline productivity 2.0, the expected direct harvesting rate before considering local stock availability is approximately:

* food acquired per tick: `2 / 11 ≈ 0.18`;
* water acquired per tick: `2 / 11 ≈ 0.18`.

The metabolic requirement is:

* food required per tick: 1.0;
* water required per tick: 1.0.

Random action selection is therefore structurally unable to replace resources at the required average rate.

The observed extinction is consistent with this mechanism.

This explanation follows directly from the imposed action probabilities and metabolism rules and must not be interpreted as an emergent phenomenon.

---

## 10. Oracle equilibrium

OracleSurvivalPolicy finishes all three 2,000-tick runs with:

* all 256 agents alive;
* health equal to 100;
* aggregate food and water inventories close to their initial aggregate level.

Initial aggregate inventory for each resource is:

`256 × 20 = 5,120`

Final aggregate inventories are approximately 5,092–5,102.

This suggests that OracleSurvivalPolicy reaches a stable resource-management regime rather than accumulating unlimited inventory.

The global resource field also remains close to capacity.

The M0 baseline should therefore be understood as a deliberately forgiving viability environment rather than a scarcity experiment.

---

## 11. Confirmed Oracle synchronization pattern

Temporal analysis confirms a deterministic period-2 aggregate cycle in all three `OracleSurvivalPolicy` runs.

After an initial transient covering approximately ticks 0–20, the trajectories enter a repeating two-tick pattern that persists through tick 2,000.

Across seeds 0, 1, and 2:

* the period is exactly 2 ticks;
* the pattern persists from tick 21 through tick 2,000;
* this corresponds to 990 complete repetitions;
* aggregate alive-agent food minus water inventory alternates between `512` and `0`;
* aggregate world food minus water stock alternates between `-256` and `256`.

The pre-equilibrium world-resource difference reaches seed-dependent minima of:

* seed 0: `-266`;
* seed 1: `-270`;
* seed 2: `-265`.

The most plausible explanation is the symmetry imposed by the M0 baseline:

* identical food and water needs;
* identical initial inventories;
* identical food and water productivity;
* spatially homogeneous resources;
* deterministic survival-oriented behavior;
* food-first targeting when food and water survival times are exactly equal.

The temporal evidence therefore supports the existence of a highly synchronized deterministic cycle.

However, this result must **not** be interpreted as emergent social behavior.

The agents do not communicate, coordinate, observe global population state, or intentionally synchronize with one another.

The cycle is instead consistent with many identical deterministic policies independently responding to identical or near-identical local conditions under symmetric world rules.

A future ablation experiment can test this causal interpretation by breaking one symmetry at a time, for example:

* randomizing initial food/water inventories;
* introducing heterogeneous productivity;
* changing the food-first tie rule;
* introducing spatial resource heterogeneity.

Until such ablations are performed, the mechanism remains a strongly supported interpretation rather than a demonstrated causal decomposition.

---

## 12. Planned temporal analysis

The accompanying analysis script will compare all six trajectories.

Planned plots:

1. alive agents vs tick;
2. mean health of living agents vs tick;
3. total alive-agent food inventory vs tick;
4. total alive-agent water inventory vs tick;
5. total world food vs tick;
6. total world water vs tick.

The analysis will also investigate whether Oracle trajectories contain a persistent periodic oscillation.

No trajectory will be extrapolated beyond the tick at which a run actually terminated.

---

## 13. Scientific interpretation

M0 should be interpreted as infrastructure validation, not as a civilization experiment.

The experiment demonstrates that:

* the environment is survivable;
* policy quality materially affects survival;
* extinction can occur without ecological resource exhaustion;
* the same baseline behavior is qualitatively consistent across three seeds;
* the headless runner can produce reproducible quantitative trajectories suitable for later analysis.

It does **not** demonstrate:

* cooperation;
* specialization;
* markets;
* social organization;
* settlements;
* hierarchy;
* institutions;
* learning;
* emergent intelligence.

Those phenomena are outside M0.

---

## 14. Limitations

This experiment has important limitations.

### Small seed count

Only three seeds were evaluated.

This is sufficient for the M0 viability sanity check but not for strong statistical claims.

### Extremely simple policies

RandomPolicy and OracleSurvivalPolicy represent intentionally extreme controls.

The experiment does not yet test intermediate levels of competence.

### Homogeneous environment

Resources are spatially homogeneous and highly abundant.

There is little ecological reason for migration, competition, specialization or cooperation.

### Homogeneous agents

All agents have identical productivity and physical capabilities.

There is no comparative advantage.

### No learning

Neither policy learns during its lifetime.

### No social mechanics

Agents cannot yet:

* trade;
* communicate;
* transfer resources;
* form explicit social relationships;
* fight.

M0 therefore cannot yet produce most of the social phenomena ECB is ultimately intended to study.

---

## 15. Emergence status

**No claim of emergent civilization behavior is made from M0.**

The observations in this experiment concern:

* ecological viability;
* policy-dependent survival;
* deterministic population dynamics.

Any apparent population-level pattern must be compared against the imposed mechanics and policy structure before being described as emergent.

The purpose of M0 is to establish a trustworthy experimental substrate on which later emergence claims can be tested.
