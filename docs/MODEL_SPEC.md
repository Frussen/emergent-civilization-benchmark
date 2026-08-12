# ECB Model Specification

**Version:** MVP v0.1 draft
**Project:** Emergent Civilization Benchmark

This document defines the scientific world rules and architectural constraints of ECB.

Anything not specified here must not be silently invented by an implementation.

---

## 1. Purpose of MVP v0.1

ECB v0.1 models a spatial society of autonomous agents living in a shared environment containing limited renewable resources.

The initial model is intended to establish a minimal substrate on which later versions can study:

- survival;
- resource competition;
- spatial clustering;
- specialization;
- exchange;
- cooperation;
- conflict;
- social memory;
- communication;
- institutions;
- heterogeneous cognitive capability;
- long-horizon autonomous agency.

MVP v0.1 does not claim to model:

- money;
- governments;
- laws;
- formal institutions;
- occupations;
- explicit social classes;
- explicit tribes;
- explicit leadership;
- natural language;
- reproduction or biological evolution.

These concepts must either emerge from simpler mechanisms or be introduced explicitly by a later model specification.

---

## 2. Scientific separation

ECB distinguishes four categories.

### 2.1 Imposed mechanism

A world rule explicitly defined by this specification.

Examples:

- metabolism;
- movement;
- resource regeneration;
- local observation.

### 2.2 Agent policy

A decision algorithm controlling an agent.

Examples:

- random behavior;
- reactive heuristics;
- memory-based learning;
- planning;
- LLM reasoning.

### 2.3 Derived metric

An external measurement that does not directly affect the world.

Examples:

- Gini coefficient;
- network centrality;
- spatial clustering;
- specialization index.

### 2.4 Emergent phenomenon

A persistent population-level structure or behavior that is not directly represented by a world variable or rule.

A phenomenon must not be called emergent merely because it appears visually in one run.

---

## 3. Determinism and reproducibility

A run is defined by:

- complete model configuration;
- root seed;
- initial agent population and actual initial agent IDs;
- agent policies and policy configuration;
- sequence of external interventions.

Given identical values for these inputs, non-LLM simulation components must produce identical state transitions.

All stochastic behavior must use project-controlled seeded random number generators.

Hidden or unseeded randomness is forbidden.

External LLM calls are treated as policy outputs and must be logged so that an experiment can later be replayed deterministically from recorded outputs.

### 3.1 RNG streams

Initialization, policy behavior, and action resolution may use separate deterministically derived RNG streams.

The derivation of those streams must itself be deterministic from the run seed.

Randomness used by one subsystem must not be consumed unnecessarily by another subsystem.

In particular, action-resolution RNG must be consumed only where the model explicitly requires stochastic resolution.

In M0, every agent owns an independent policy RNG stream derived deterministically from the root seed and that agent's stable ID.

One agent's RNG draws must never consume or alter another agent's policy RNG sequence.

### 3.2 World-state hash

ECB defines a `world_state_hash`.

The world-state hash represents the scientific physical state of the simulated world at a particular tick.

It must include all physical state necessary to identify that world state, including at minimum:

- tick;
- living/dead agent state as represented by the world;
- agent positions;
- health;
- inventories;
- productivity values where part of physical agent state;
- cell food stocks;
- cell water stocks.

It does not need to include:

- logs;
- metrics derived from the world;
- RNG internals;
- policy internal state.

The world-state hash is used for:

- deterministic action replay;
- comparing headless and Visual Mode trajectories;
- detecting unintended changes in physical simulation state.

Equal world-state hashes do not, by themselves, guarantee identical future trajectories.

### 3.3 Execution-state hash

ECB also defines an `execution_state_hash`.

The execution-state hash represents everything required for deterministic continuation of a run, subject to the same software version and same future external inputs.

It must include:

- the complete world state;
- future-relevant model configuration;
- all project-controlled RNG states;
- policy identity;
- policy configuration;
- policy internal state.

Policy state included in this hash must use deterministic serialization.

Policies expose their continuation-relevant state explicitly through the ECB policy-state interface. The execution-state hash uses only this declared state; it must not introspect arbitrary Python object graphs.

Canonical policy state in M0 is restricted to:

- `None`;
- booleans;
- integers;
- finite floating-point values;
- strings;
- ECB enum members;
- built-in lists and tuples containing canonical values;
- built-in sets and frozensets containing canonical values;
- built-in dictionaries from canonical keys to canonical values.

Arbitrary subclasses of these built-in canonical types are not supported.

Container types are preserved explicitly. Mapping and set-like values use deterministic canonical ordering for hashing.

Arbitrary Python object identity, alias topology, closures, callables, and undeclared implementation internals are outside the continuation-state contract. A policy whose declared state cannot be represented using the supported canonical values must be rejected for continuation hashing rather than hashed incompletely.

Two equal execution-state hashes under the same software version and future external inputs must represent equivalent deterministic continuation states.

### 3.4 Action replay

Action replay bypasses normal policy deliberation and applies a recorded sequence of actions to the simulation.

Action replay guarantees reproduction of the physical world trajectory and therefore the corresponding `world_state_hash` sequence.

Action replay does not claim to reproduce continuation-equivalent policy RNG state.

In particular, replay must not consume policy RNG merely to imitate policy calls that are being bypassed.

Therefore a replayed run may match the original world-state hashes while having a different `execution_state_hash`.

Continuation-equivalent restoration requires restoring a complete execution state rather than merely replaying actions.

---

## 4. Time

Time is discrete.

Simulation time advances through integer ticks:

`t = 0, 1, 2, ...`

Each tick consists logically of:

1. observation;
2. agent decision;
3. action resolution;
4. metabolism;
5. ecological regeneration;
6. metrics;
7. event finalization/logging.

All agents observe the same logical world time before actions for that tick are resolved.

The global simulation tick is not included in M0 policy observations.

Agent iteration order must not create systematic advantages.

Events may be generated during the simulation phase in which they occur, such as movement resolution, harvesting, or metabolism.

Those event objects are collected/finalized as part of the logging stage.

Event creation and logging must never affect world mechanics.

### 4.1 Simulation time vs wall-clock time

Simulation time is independent from real execution time.

If an external policy such as an LLM takes several seconds to deliberate, the simulated world does not advance during that delay.

Therefore:

- API latency;
- network latency;
- machine performance;

must not influence simulated outcomes in the canonical benchmark mode.

A future asynchronous real-time mode may deliberately relax this rule, but it will be considered a separate experimental condition.

---

## 5. World geometry

The world is a finite two-dimensional rectangular grid.

Default baseline:

- width: `64`;
- height: `64`;
- initial population: `256 agents`.

Coordinates are integer pairs `(x, y)` satisfying:

`0 <= x < width`

`0 <= y < height`

The world is not toroidal.

Movement outside the world boundary is illegal.

For directional conventions in M0:

- north decreases `y`;
- south increases `y`;
- east increases `x`;
- west decreases `x`.

Canonical coordinate ordering is lexicographic `(x, y)`.

---

## 6. Spatial occupancy

Multiple agents may occupy the same grid cell.

This is intentional.

MVP v0.1 must not introduce:

- collision mechanics;
- territorial ownership;
- blocking;
- chokepoints;

merely as side effects of grid occupancy.

Agent density per cell remains observable and measurable.

Single-occupancy may later become an explicit experimental condition.

---

## 7. Resources

The world initially contains two resource types:

- food;
- water.

Each cell contains independent stocks for both resources.

For every resource `r`:

- `stock_r >= 0`;
- `capacity_r >= 0`;
- `regeneration_r >= 0`.

Invariant:

`0 <= stock_r <= capacity_r`

Resources are represented as divisible real-valued quantities.

### 7.1 Baseline M0 resource initialization

M0 uses a spatially homogeneous baseline resource field.

For every grid cell:

- food capacity: `20.0`;
- food initial stock: `20.0`;
- food regeneration rate: `1.0`;
- water capacity: `20.0`;
- water initial stock: `20.0`;
- water regeneration rate: `1.0`.

All cells use identical baseline values.

Spatially heterogeneous or procedurally generated resource distributions are explicitly deferred to later experimental configurations.

These values are calibration defaults, not claims of ecological realism.

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

- unique immutable ID;
- position;
- food inventory;
- water inventory;
- health;
- food productivity;
- water productivity;
- policy state.

The engine must not contain built-in variables representing:

- profession;
- class;
- faction;
- tribe;
- leadership;
- global reputation;
- political power.

Those concepts may later be inferred analytically or explicitly introduced in a future specification.

---

## 10. Population dynamics

MVP v0.1 begins with a fixed initial cohort.

There are:

- no births;
- no reproduction;
- no offspring;
- no heredity;
- no mutation;
- no generational replacement.

Agents may die.

Therefore population size is non-increasing during a v0.1 run.

This is deliberate: within-lifetime adaptation must remain scientifically distinguishable from evolutionary selection.

Reproduction may later be introduced as an optional experimental regime.

Dead agents may remain represented in stored historical world state with zero health, but they are not part of the active population.

---

## 11. Health

Default initial health:

`health = 100`

Invariant:

`0 <= health <= 100`

An agent dies when:

`health <= 0`

Dead agents:

- cannot act;
- do not consume resources;
- do not occupy active-world space for observation purposes;
- are removed from future observation/action cycles.

MVP v0.1 contains no passive health regeneration.

---

## 12. Initial reserves

Agents must not begin on the verge of starvation.

Baseline defaults:

- initial food inventory: `20.0`;
- initial water inventory: `20.0`.

These reserves provide an initial exploration window.

Their values are model parameters and must be included in run configuration.

---

## 13. Metabolism

Every living agent requires both food and water every tick.

Baseline:

- `food_need = 1.0`;
- `water_need = 1.0`.

During metabolism:

`food_consumed = min(food_inventory, food_need)`

`water_consumed = min(water_inventory, water_need)`

Deficits are:

`food_deficit = food_need - food_consumed`

`water_deficit = water_need - water_consumed`

Health loss is:

`health_loss = food_deficit * food_health_penalty + water_deficit * water_health_penalty`

No valid transition may leave non-finite scientific state. Before committing an arithmetic transition that would produce `NaN` or infinity, the engine raises an explicit simulation numerical/invariant error and leaves the physical world state unchanged.

Baseline:

- `food_health_penalty = 1.0`;
- `water_health_penalty = 1.0`.

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

- cell stock decreases by `actual_amount`;
- agent inventory increases by `actual_amount`.

No profession variable exists.

If persistent specialization later appears, it must result from agent behavior rather than a predefined occupational role.

### 14.1 Baseline M0 agent initialization

The baseline M0 population contains 256 agents.

Each agent starts with:

- health: `100`;
- food inventory: `20.0`;
- water inventory: `20.0`;
- food productivity: `2.0`;
- water productivity: `2.0`.

Productivity is homogeneous in M0.

Heterogeneous productivity distributions are deferred to later experiments on comparative advantage and specialization.

### 14.2 Initial agent placement

Each initial agent position is sampled independently and uniformly across all valid grid cells using the project-controlled seeded initialization RNG.

Sampling is with replacement.

Therefore multiple agents may initially occupy the same cell.

Agent IDs or creation order must not affect the position distribution.

---

## 15. Observation model

ECB is partially observable.

Each agent receives an `Observation`.

### 15.1 Self information

The observation contains:

- own ID;
- position;
- health;
- food inventory;
- water inventory;
- own productivity values.

### 15.2 Local spatial information

Within the observation radius it contains:

- relative cell positions;
- local food stocks;
- local water stocks;
- other visible living agents.

Baseline observation radius:

`3`

Distance metric:

Chebyshev distance.

The observing agent must not appear in its own `visible_agents` collection because its state is already represented explicitly as self information.

Visible-agent information in M0 contains only information exposed by the Observation schema and must not leak hidden policy state or other inaccessible internal state.

`visible_agents` uses deterministic canonical ordering by absolute cell coordinate `(x, y)`, followed by lexicographic agent ID within a cell.

Agents do not automatically receive:

- complete world state;
- global resource totals;
- global wealth;
- aggregate benchmark metrics;
- hidden policy state of other agents;
- global interaction networks;
- analytical community assignments.

---

## 16. Agent-policy separation

Agent bodies and decision policies are separate.

Conceptually:

`Policy: Observation -> Action`

Policies receive observations and may update their own policy state.

Policies must never mutate `WorldState` directly.

All world changes occur through validated actions resolved by the engine.

This interface must remain compatible with:

- scripted policies;
- learning policies;
- planning policies;
- reinforcement-learning policies;
- future LLM policies.

Changing policy must not require changing the agent's physical body.

Each M0 agent owns a distinct policy instance. Shared mutable policy instances between agents are not supported.

Policy assignment is explicit. The simulation must not silently install a default policy when none is supplied.

Every policy exposes through the ECB policy-state interface:

- canonical policy configuration sufficient to identify its setup;
- canonical continuation state containing every mutable value that can affect future decisions.

### 16.1 Action typing and validation

Actions are typed model objects.

Enum-valued fields such as action kind, movement direction, and resource type must contain actual members of the corresponding enum type.

Malformed raw values such as the string `"food"` supplied where a `Resource` enum is required are invalid input and must be rejected rather than silently coerced or interpreted as another value.

---

## 17. Learning

MVP M0 does not require agents to learn.

Initial policies may be fixed.

In later milestones, agents may adapt during their own lifetime by modifying private `policy_state`.

This may include:

- remembered resource locations;
- estimates of environmental value;
- memories of interactions;
- learned partner preferences;
- action-value estimates;
- plans.

A neural network is not required for learning.

Possible later learning mechanisms include:

- memory-based heuristics;
- bandit learning;
- tabular value learning;
- planning;
- neural reinforcement learning.

Within-lifetime learning must remain distinct from reproduction and evolutionary selection.

---

## 18. M0 control policies

### 18.1 RandomPolicy

`RandomPolicy` is a simple M0 baseline policy.

At each decision point it samples uniformly from the complete M0 primitive action set:

- `WAIT`;
- eight directional `MOVE` actions;
- `HARVEST(food)`;
- `HARVEST(water)`.

It uses only its project-controlled policy RNG stream.

It has no access to `WorldState`.

Its purpose is to provide a weak behavioral control, not a model of realistic behavior.

### 18.2 OracleSurvivalPolicy

M0 includes a test-only `OracleSurvivalPolicy` used to verify ecological viability.

Despite its name, this policy receives only the standard `Observation` and has no direct access to `WorldState` or hidden information.

At each decision point:

1. Compute expected remaining survival time for food and water from current inventory and metabolic need.
2. Select the resource with the lower remaining survival time as the target.
3. If food and water have exactly equal remaining survival time, target food.
4. If the current cell contains at least one full harvest amount of the target resource, `HARVEST` it.
5. Otherwise select the observed cell containing the greatest stock of the target resource.
6. Move one step toward that cell.
7. Ties between candidate cells are resolved first by shortest distance and then by canonical lexicographic coordinate order `(x, y)`.
8. If no observed cell contains the target resource, `WAIT`.

If the selected best target cell is the current cell and contains a positive amount smaller than one full harvest amount, `HARVEST` the available partial amount instead of waiting.

`OracleSurvivalPolicy` is not a benchmark participant and must not be used as evidence of emergent intelligence.

### 18.3 Baseline viability criterion

For M0 validation, the baseline configuration must be simulated for 2,000 ticks using `OracleSurvivalPolicy` for every agent.

Across seeds:

- `0`;
- `1`;
- `2`;

the population survival fraction at tick 2,000 must be at least `0.95` for each run.

Failure indicates either:

- an implementation bug;
- an internally inconsistent baseline;
- or a baseline ecology that requires scientific recalibration.

This criterion is a software/scientific sanity check, not a benchmark score.

Longer 10,000+ tick viability experiments may be run outside the fast development-test suite.

The RandomPolicy control should perform meaningfully worse than the survival-oriented control under the baseline calibration; this is used as a sanity check that policy quality can affect outcomes.

---

## 19. Action vocabulary

The planned ECB v0.1 vocabulary includes:

- `WAIT`;
- `MOVE`;
- `HARVEST`;
- `POST_TRADE`;
- `ACCEPT_TRADE`;
- `CANCEL_TRADE`;
- `TRANSFER`;
- `RAID`.

Implementation is incremental.

M0 implements only:

- `WAIT`;
- `MOVE`;
- `HARVEST`.

No other mechanics may be implemented before their rules are added to this specification.

### 19.1 Explicit action completeness

For externally supplied action maps, every living agent must have an explicit valid action for the tick.

A missing action is invalid input and must not silently resolve to `WAIT`.

Adapters or callers that intend inactivity or timeout behavior must explicitly supply `WAIT`.

---

## 20. WAIT

`WAIT` performs no intentional world interaction during action resolution.

Metabolism still occurs.

---

## 21. MOVE

`MOVE` changes position by one cell.

Allowed directions:

- north;
- north-east;
- east;
- south-east;
- south;
- south-west;
- west;
- north-west.

Movement cost in MVP v0.1:

`0`

Movement outside the grid is illegal.

An illegal movement resolves as `WAIT` and emits an invalid-action event.

---

## 22. HARVEST

`HARVEST` specifies one resource:

- food;
- water.

Harvesting occurs on the agent's current cell after movement resolution for the tick.

Quantity follows the productivity rule.

If the selected resource stock is zero, harvested quantity is zero.

### 22.1 Contested harvesting

A contested harvest group consists of agents attempting to harvest the same resource from the same cell during the same tick.

Contested groups must be processed in deterministic canonical order.

Resolution RNG is used only within a contested group when action ordering can affect the allocation of finite stock.

If a harvest is uncontested, or if every harvester in a group can receive its full requested amount regardless of order, resolution RNG must not be consumed for that group.

When ordering can affect allocation, the competing agents are placed in a seeded randomized order and harvesting is resolved sequentially in that order.

This randomization must be reproducible from the run seed and current execution state.

Agent creation order must not create systematic harvest priority.

---

## 23. Action resolution

All actions for tick `t` are selected before resolution begins.

For M0:

1. movement actions resolve;
2. harvest actions resolve.

`WAIT` requires no intentional resolution.

Policies do not mutate the world directly.

The resolution layer validates and applies actions according to this specification.

Resolution randomness must be isolated from policy and initialization randomness as described in the RNG rules.

---

## 24. Future communication architecture

Communication is not implemented in M0.

ECB will distinguish communication infrastructure from cognitive capability.

An agent does not need to use an LLM or external API in order to communicate.

Three communication regimes are planned.

### 24.1 Structured protocol mode

Agents exchange machine-readable messages with explicitly defined semantics.

Examples may include:

- trade proposal;
- acceptance;
- rejection;
- counterproposal;
- resource-location information.

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

- health;
- productivity;
- movement speed;
- observation radius;
- inventory capacity;
- physical privileges.

The difference should consist primarily in decision capability.

Potential LLM advantages include:

- long-horizon planning;
- semantic memory;
- negotiation;
- adaptation to novel situations;
- strategic reasoning;
- multi-agent coordination.

---

## 26. Hierarchical LLM control

The canonical future design must not require one LLM call per agent per simulation tick.

An LLM policy may deliberate at a slower strategic cadence.

Example:

`LLM deliberation -> multi-tick plan -> fast local controller -> primitive actions`

Replanning may occur:

- periodically;
- when a goal is completed;
- after significant environmental change;
- after receiving an important message;
- when survival thresholds are crossed.

The number of model calls is therefore part of policy design rather than a requirement imposed by the engine.

---

## 27. LLM memory

Long-term agent memory must not depend solely on an opaque conversational context.

ECB should support explicit inspectable policy memory such as:

### 27.1 Episodic memory

- encounters;
- trades;
- conflicts;
- received messages;
- discovered locations.

### 27.2 Semantic memory

- inferred reliability of other agents;
- learned resource geography;
- learned environmental regularities.

### 27.3 Planning memory

- goals;
- commitments;
- current plan;
- unresolved tasks.

Explicit memory allows:

- inspection;
- ablation;
- reset experiments;
- comparisons between different policies;
- replacement of one model while preserving an agent's history.

---

## 28. Future AGI-shock experiments

A central future experimental regime is:

**Pre-capability society -> capability intervention -> post-intervention society**

The preferred controlled intervention is policy replacement.

Example:

`ReactivePolicy -> highly capable LLMPolicy`

while preserving the same:

- agent body;
- inventories;
- memories when experimentally appropriate;
- physical capabilities;
- local information access.

This isolates increased cognitive capability from physical privilege.

Metrics may examine changes in:

- wealth;
- productivity;
- trade centrality;
- inequality;
- cooperation;
- conflict;
- coalition structure;
- sustainability;
- concentration of power.

Communication availability itself should be an experimental variable.

---

## 29. LLM compute metrics

Future LLM experiments should record computational expenditure separately from simulated outcomes.

Possible metrics include:

- number of model calls;
- input tokens;
- output tokens;
- deliberations per simulated tick;
- wall-clock latency;
- plan duration before replanning.

This permits comparison between raw performance and cognitive/computational efficiency.

Wall-clock latency does not affect canonical simulated time.

---

## 30. Logging and run identity

Every run must record enough information to identify and reproduce it.

At minimum:

- complete model configuration;
- root seed;
- software version;
- actual initial agent IDs;
- policy identity;
- policy configuration sufficient to identify the policies used;
- tick;
- agent actions;
- significant world events;
- aggregate metrics.

Software identity includes the package version plus source revision information when available. A dirty working tree is marked as such when it can be detected.

Where policies have mutable internal state, reproducible checkpoints intended for continuation must also preserve the relevant policy state and RNG state.

For external model policies, additionally record:

- model identifier;
- policy configuration;
- model inputs or reproducible observation representation where appropriate;
- resulting structured actions;
- relevant usage metadata.

Logging must not alter outcomes.

Events may be generated when their corresponding world event occurs, but event collection/finalization belongs to the logging stage.

---

## 31. Headless and Visual Mode equivalence

The simulation core must have no dependency on visualization.

Visual Mode consumes:

- snapshots;
- metrics;
- events.

It must never alter the simulation.

For deterministic policies:

`headless(config, seed)`

and:

`visual(config, seed)`

must produce identical physical state trajectories and therefore identical `world_state_hash` sequences.

Visual rendering frequency is independent from simulation tick frequency.

Visual Mode must not consume simulation RNG or otherwise alter execution state.

---

## 32. Visual Mode target

The Visual Mode must eventually support:

- play;
- pause;
- single-step;
- adjustable speed;
- zoom and pan;
- agent inspection;
- agent history;
- resource overlays;
- wealth overlays;
- reputation overlays where analytically defined;
- community overlays;
- trade visualization;
- conflict visualization;
- event feed;
- aggregate metric plots.

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

- professions must not be predefined if claiming division of labor;
- group IDs must not be predefined if claiming group formation;
- a global reputation score must not be predefined if claiming reputation emergence;
- leadership bonuses must not be predefined if claiming hierarchy emergence.

---

## 34. M0 implementation boundary

M0 contains only:

- deterministic `WorldState`;
- project-controlled seeded RNG streams;
- configurable rectangular grid with default size 64×64;
- multi-agent cell occupancy;
- food;
- water;
- deterministic resource regeneration;
- agent state;
- fixed initial cohort;
- death but no birth;
- metabolism;
- initial resource reserves;
- productivity;
- local observation;
- typed and validated M0 actions;
- `WAIT`;
- `MOVE`;
- `HARVEST`;
- `RandomPolicy`;
- `OracleSurvivalPolicy`;
- invariant verification;
- `world_state_hash`;
- `execution_state_hash`;
- deterministic action replay tests;
- viability calibration tests;
- run metadata sufficient to identify reproducibility inputs.

Explicitly excluded from M0:

- neural networks;
- reproduction;
- evolution;
- trade;
- social reputation;
- interaction memory;
- transfer;
- conflict;
- communication;
- natural language;
- symbolic language;
- coalitions;
- institutions;
- markets;
- money;
- explicit settlements;
- Visual Mode;
- Mesa integration;
- PettingZoo integration;
- reinforcement learning;
- LLM policies.

These belong to later milestones and require explicit specification before implementation.
