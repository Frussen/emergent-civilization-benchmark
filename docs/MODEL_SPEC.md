# ECB Model Specification

**Version:** MVP v0.1 draft
**Project:** Emergent Civilization Benchmark

This document defines the scientific world rules and architectural constraints of ECB.

Anything not specified here must not be silently invented by an implementation.

---

## 1. Purpose of MVP v0.1

ECB v0.1 models a spatial society of autonomous agents living in a shared environment containing limited renewable resources.

The initial model is intended to establish a minimal substrate on which later versions can study:

* survival;
* resource competition;
* spatial clustering;
* specialization;
* exchange;
* cooperation;
* conflict;
* social memory;
* communication;
* institutions;
* heterogeneous cognitive capability;
* long-horizon autonomous agency.

MVP v0.1 does not claim to model:

* money;
* governments;
* laws;
* formal institutions;
* occupations;
* explicit social classes;
* explicit tribes;
* explicit leadership;
* natural language;
* reproduction or biological evolution.

These concepts must either emerge from simpler mechanisms or be introduced explicitly by a later model specification.

---

## 2. Scientific separation

ECB distinguishes four categories.

### 2.1 Imposed mechanism

A world rule explicitly defined by this specification.

Examples:

* metabolism;
* movement;
* resource regeneration;
* local observation.

### 2.2 Agent policy

A decision algorithm controlling an agent.

Examples:

* random behavior;
* reactive heuristics;
* memory-based learning;
* planning;
* LLM reasoning.

### 2.3 Derived metric

An external measurement that does not directly affect the world.

Examples:

* Gini coefficient;
* network centrality;
* spatial clustering;
* specialization index.

### 2.4 Emergent phenomenon

A persistent population-level structure or behavior that is not directly represented by a world variable or rule.

A phenomenon must not be called emergent merely because it appears visually in one run.

---

## 3. Determinism

A run is defined by:

* model configuration;
* initial seed;
* initial agent population;
* agent policies;
* sequence of external interventions.

Given identical values for these inputs, non-LLM simulation components must produce identical state transitions.

All stochastic behavior must use project-controlled seeded random number generators.

Hidden or unseeded randomness is forbidden.

External LLM calls are treated as policy outputs and must be logged so that an experiment can later be replayed deterministically from recorded outputs.

---

## 4. Time

Time is discrete.

Simulation time advances through integer ticks:

`t = 0, 1, 2, ...`

Each tick consists of:

1. observation;
2. agent decision;
3. action resolution;
4. metabolism;
5. ecological regeneration;
6. metrics;
7. event logging.

All agents observe the same logical world time before actions for that tick are resolved.

Agent iteration order must not create systematic advantages.

### 4.1 Simulation time vs wall-clock time

Simulation time is independent from real execution time.

If an external policy such as an LLM takes several seconds to deliberate, the simulated world does not advance during that delay.

Therefore:

* API latency;
* network latency;
* machine performance;

must not influence simulated outcomes in the canonical benchmark mode.

A future asynchronous real-time mode may deliberately relax this rule, but it will be considered a separate experimental condition.

---

## 5. World geometry

The world is a finite two-dimensional rectangular grid.

Default baseline:

* width: `64`;
* height: `64`;
* initial population: `256 agents`.

Coordinates are integer pairs `(x, y)` satisfying:

`0 <= x < width`

`0 <= y < height`

The world is not toroidal.

Movement outside the world boundary is illegal.

---

## 6. Spatial occupancy

Multiple agents may occupy the same grid cell.

This is intentional.

MVP v0.1 must not introduce:

* collision mechanics;
* territorial ownership;
* blocking;
* chokepoints;

merely as side effects of grid occupancy.

Agent density per cell remains observable and measurable.

Single-occupancy may later become an explicit experimental condition.

---

## 7. Resources

The world initially contains two resource types:

* food;
* water.

Each cell contains independent stocks for both resources.

For every resource `r`:

* `stock_r >= 0`;
* `capacity_r >= 0`;
* `regeneration_r >= 0`.

Invariant:

`0 <= stock_r <= capacity_r`

Resources are represented as divisible real-valued quantities.

---

## 8. Resource regeneration

After metabolism, each resource regenerates according to:

`new_stock = min(capacity, current_stock + regeneration_rate)`

Regeneration is deterministic in MVP v0.1.

Setting:

`regeneration_rate = 0`

creates an exhaustible resource without introducing a separate resource class.

---

## 9. Agent state

Every agent has:

* unique immutable ID;
* position;
* food inventory;
* water inventory;
* health;
* food productivity;
* water productivity;
* policy state.

The engine must not contain built-in variables representing:

* profession;
* class;
* faction;
* tribe;
* leadership;
* global reputation;
* political power.

Those concepts may later be inferred analytically or explicitly introduced in a future specification.

---

## 10. Population dynamics

MVP v0.1 begins with a fixed initial cohort.

There are:

* no births;
* no reproduction;
* no offspring;
* no heredity;
* no mutation;
* no generational replacement.

Agents may die.

Therefore population size is non-increasing during a v0.1 run.

This is deliberate: within-lifetime adaptation must remain scientifically distinguishable from evolutionary selection.

Reproduction may later be introduced as an optional experimental regime.

---

## 11. Health

Default initial health:

`health = 100`

Invariant:

`0 <= health <= 100`

An agent dies when:

`health <= 0`

Dead agents:

* cannot act;
* do not consume resources;
* are removed from future observation/action cycles.

MVP v0.1 contains no passive health regeneration.

---

## 12. Initial reserves

Agents must not begin on the verge of starvation.

Baseline defaults:

* initial food inventory: `20`;
* initial water inventory: `20`.

These reserves provide an initial exploration window.

Their values are model parameters and must be included in run configuration.

---

## 13. Metabolism

Every living agent requires both food and water every tick.

Baseline:

* `food_need = 1.0`;
* `water_need = 1.0`.

During metabolism:

`food_consumed = min(food_inventory, food_need)`

`water_consumed = min(water_inventory, water_need)`

Deficits are:

`food_deficit = food_need - food_consumed`

`water_deficit = water_need - water_consumed`

Health loss is:

`health_loss = food_deficit * food_health_penalty + water_deficit * water_health_penalty`

Baseline:

* `food_health_penalty = 1.0`;
* `water_health_penalty = 1.0`.

Therefore complete deprivation of both resources causes a baseline loss of two health points per tick after reserves are exhausted.

These values are baseline parameters and must be calibrated through viability experiments rather than assumed to represent biological realism.

---

## 14. Productivity and harvesting

Each agent has:

`food_productivity > 0`

and:

`water_productivity > 0`

Productivity determines harvesting effectiveness.

For resource `r`:

`requested_amount = base_harvest_amount * productivity_r`

`actual_amount = min(requested_amount, cell_resource_stock)`

Baseline:

`base_harvest_amount = 1.0`

Resource conservation must hold exactly:

* cell stock decreases by `actual_amount`;
* agent inventory increases by `actual_amount`.

No profession variable exists.

If persistent specialization later appears, it must result from agent behavior rather than a predefined occupational role.

---

## 15. Observation model

ECB is partially observable.

Each agent receives an `Observation`.

### Self information

The observation contains:

* own ID;
* position;
* health;
* food inventory;
* water inventory;
* own productivity values.

### Local spatial information

Within the observation radius it contains:

* relative cell positions;
* local food stocks;
* local water stocks;
* visible agents.

Baseline observation radius:

`3`

Distance metric:

Chebyshev distance.

Agents do not automatically receive:

* complete world state;
* global resource totals;
* global wealth;
* aggregate benchmark metrics;
* hidden policy state of other agents;
* global interaction networks;
* analytical community assignments.

---

## 16. Agent-policy separation

Agent bodies and decision policies are separate.

Conceptually:

`Policy: Observation -> Action`

Policies receive observations and may update their own policy state.

Policies must never mutate `WorldState` directly.

All world changes occur through validated actions resolved by the engine.

This interface must remain compatible with:

* scripted policies;
* learning policies;
* planning policies;
* reinforcement-learning policies;
* future LLM policies.

Changing policy must not require changing the agent's physical body.

---

## 17. Learning

MVP M0 does not require agents to learn.

Initial policies may be fixed.

In later milestones, agents may adapt during their own lifetime by modifying private `policy_state`.

This may include:

* remembered resource locations;
* estimates of environmental value;
* memories of interactions;
* learned partner preferences;
* action-value estimates;
* plans.

A neural network is not required for learning.

Possible later learning mechanisms include:

* memory-based heuristics;
* bandit learning;
* tabular value learning;
* planning;
* neural reinforcement learning.

Within-lifetime learning must remain distinct from reproduction and evolutionary selection.

---

## 18. Viability requirement

ECB must not guarantee survival.

Death must remain a possible consequence of poor strategy, scarcity or competition.

However, the baseline ecology must make long-term survival physically achievable by a sufficiently capable policy.

The project must therefore include a non-benchmark control policy such as:

`OracleSurvivalPolicy`

Its purpose is not to participate in scientific comparisons but to verify that the configured environment is survivable.

A baseline configuration is invalid if even a strong survival-oriented control policy predictably drives the population to extinction.

The calibration suite should also verify that weaker policies perform meaningfully worse, ensuring that strategy matters.

---

## 19. Action vocabulary

The planned ECB v0.1 vocabulary includes:

* `WAIT`;
* `MOVE`;
* `HARVEST`;
* `POST_TRADE`;
* `ACCEPT_TRADE`;
* `CANCEL_TRADE`;
* `TRANSFER`;
* `RAID`.

Implementation is incremental.

M0 implements only:

* `WAIT`;
* `MOVE`;
* `HARVEST`.

No other mechanics may be implemented before their rules are added to this specification.

---

## 20. WAIT

`WAIT` performs no intentional world interaction during action resolution.

Metabolism still occurs.

---

## 21. MOVE

`MOVE` changes position by one cell.

Allowed directions:

* north;
* north-east;
* east;
* south-east;
* south;
* south-west;
* west;
* north-west.

Movement cost in MVP v0.1:

`0`

Movement outside the grid is illegal.

An illegal movement resolves as `WAIT` and emits an invalid-action event.

---

## 22. HARVEST

`HARVEST` specifies one resource:

* food;
* water.

Harvesting occurs on the agent's current cell.

Quantity follows the productivity rule.

If the selected resource stock is zero, harvested quantity is zero.

---

## 23. Action resolution

All actions for tick `t` are selected before resolution begins.

For M0:

1. movement resolves;
2. harvesting resolves.

`WAIT` requires no resolution.

When multiple agents harvest the same limited stock, resolution order must not depend on agent creation order.

A seeded randomized contested-resolution order must be used.

It must be reproducible.

---

## 24. Future communication architecture

Communication is not implemented in M0.

ECB will distinguish communication infrastructure from cognitive capability.

An agent does not need to use an LLM or external API in order to communicate.

Three communication regimes are planned.

### 24.1 Structured protocol mode

Agents exchange machine-readable messages with explicitly defined semantics.

Examples may include:

* trade proposal;
* acceptance;
* rejection;
* counterproposal;
* resource-location information.

Scripted agents can generate and interpret these messages entirely through local code.

An LLM policy may receive a natural-language rendering of the same structure and produce structured responses.

Therefore a future society may contain hundreds of scripted communicating agents while only one or a few agents require LLM API calls.

Structured semantics are imposed mechanisms and must never be described as emergent language.

### 24.2 Symbolic communication mode

Agents exchange sequences from a finite symbol vocabulary whose meanings are not defined by the world.

Example:

`[7, 2, 14]`

The engine transports the symbols but assigns no semantic interpretation.

Learning-capable policies may develop associations between symbols, observations and behavior.

This mode may later be used to study emergent communication protocols.

### 24.3 Natural-language mode

Agents may send text messages.

The simulation engine transports the text but does not interpret its semantic meaning.

Natural-language understanding belongs to the policy.

This mode is primarily intended for LLM agents or other policies equipped with language understanding.

---

## 25. Future LLM policy

An `LLMPolicy` must use exactly the same physical world interface as other policies.

Replacing:

`ReactivePolicy -> LLMPolicy`

must not automatically change:

* health;
* productivity;
* movement speed;
* observation radius;
* inventory capacity;
* physical privileges.

The difference should consist primarily in decision capability.

Potential LLM advantages include:

* long-horizon planning;
* semantic memory;
* negotiation;
* adaptation to novel situations;
* strategic reasoning;
* multi-agent coordination.

---

## 26. Hierarchical LLM control

The canonical future design must not require one LLM call per agent per simulation tick.

An LLM policy may deliberate at a slower strategic cadence.

Example:

`LLM deliberation -> multi-tick plan -> fast local controller -> primitive actions`

Replanning may occur:

* periodically;
* when a goal is completed;
* after significant environmental change;
* after receiving an important message;
* when survival thresholds are crossed.

The number of model calls is therefore part of policy design rather than a requirement imposed by the engine.

---

## 27. LLM memory

Long-term agent memory must not depend solely on an opaque conversational context.

ECB should support explicit inspectable policy memory such as:

### Episodic memory

* encounters;
* trades;
* conflicts;
* received messages;
* discovered locations.

### Semantic memory

* inferred reliability of other agents;
* learned resource geography;
* learned environmental regularities.

### Planning memory

* goals;
* commitments;
* current plan;
* unresolved tasks.

Explicit memory allows:

* inspection;
* ablation;
* reset experiments;
* comparisons between different policies;
* replacement of one model while preserving an agent's history.

---

## 28. Future AGI-shock experiments

A central future experimental regime is:

**Pre-capability society -> capability intervention -> post-intervention society**

The preferred controlled intervention is policy replacement.

Example:

`ReactivePolicy -> highly capable LLMPolicy`

while preserving the same:

* agent body;
* inventories;
* memories when experimentally appropriate;
* physical capabilities;
* local information access.

This isolates increased cognitive capability from physical privilege.

Metrics may examine changes in:

* wealth;
* productivity;
* trade centrality;
* inequality;
* cooperation;
* conflict;
* coalition structure;
* sustainability;
* concentration of power.

Communication availability itself should be an experimental variable.

---

## 29. LLM compute metrics

Future LLM experiments should record computational expenditure separately from simulated outcomes.

Possible metrics include:

* number of model calls;
* input tokens;
* output tokens;
* deliberations per simulated tick;
* wall-clock latency;
* plan duration before replanning.

This permits comparison between raw performance and cognitive/computational efficiency.

Wall-clock latency does not affect canonical simulated time.

---

## 30. Logging

Every run must record enough information to identify and reproduce it.

At minimum:

* complete configuration;
* seed;
* software version;
* tick;
* agent actions;
* significant world events;
* aggregate metrics.

For external model policies, additionally record:

* model identifier;
* policy configuration;
* model inputs or reproducible observation representation where appropriate;
* resulting structured actions;
* relevant usage metadata.

Logging must not alter outcomes.

---

## 31. Headless and Visual Mode equivalence

The simulation core must have no dependency on visualization.

Visual Mode consumes:

* snapshots;
* metrics;
* events.

It must never alter the simulation.

For deterministic policies:

`headless(config, seed)`

and

`visual(config, seed)`

must produce identical state trajectories.

Visual rendering frequency is independent from simulation tick frequency.

---

## 32. Visual Mode target

The Visual Mode must eventually support:

* play;
* pause;
* single-step;
* adjustable speed;
* zoom and pan;
* agent inspection;
* agent history;
* resource overlays;
* wealth overlays;
* reputation overlays where analytically defined;
* community overlays;
* trade visualization;
* conflict visualization;
* event feed;
* aggregate metric plots.

It must remain practical on a MacBook Air M1 with 8 GB RAM.

Rendering must not be coupled one-to-one with simulation ticks.

---

## 33. Emergence criteria

A phenomenon should only be described as emergent when:

1. it has a quantitative operational definition;
2. it persists through time;
3. it appears across multiple seeds;
4. it differs meaningfully from an appropriate null/control condition;
5. relevant ablations identify conditions affecting its appearance;
6. the phenomenon itself is not directly encoded as a world variable or rule.

Examples:

* professions must not be predefined if claiming division of labor;
* group IDs must not be predefined if claiming group formation;
* a global reputation score must not be predefined if claiming reputation emergence;
* leadership bonuses must not be predefined if claiming hierarchy emergence.

---

## 34. M0 implementation boundary

M0 contains only:

* deterministic `WorldState`;
* project-controlled seeded RNG;
* 64×64 configurable grid;
* multi-agent cell occupancy;
* food;
* water;
* deterministic resource regeneration;
* agent state;
* fixed initial cohort;
* death but no birth;
* metabolism;
* initial resource reserves;
* productivity;
* local observation;
* `WAIT`;
* `MOVE`;
* `HARVEST`;
* `RandomPolicy`;
* survival-oriented control policy;
* invariant verification;
* deterministic replay tests;
* viability calibration tests.

Explicitly excluded from M0:

* neural networks;
* reproduction;
* evolution;
* trade;
* social reputation;
* interaction memory;
* transfer;
* conflict;
* communication;
* natural language;
* symbolic language;
* coalitions;
* institutions;
* markets;
* money;
* explicit settlements;
* Visual Mode;
* Mesa integration;
* PettingZoo integration;
* reinforcement learning;
* LLM policies.

These belong to later milestones and require explicit specification before implementation.
