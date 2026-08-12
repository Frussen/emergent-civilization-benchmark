# ECB Architecture

## Emergent Civilization Benchmark

This document defines the software architecture of the **Emergent Civilization Benchmark (ECB)**.

ECB is intended to become a reproducible experimental environment for studying long-horizon autonomous agents, artificial societies, and candidate emergent social phenomena.

The architecture therefore has two simultaneous goals:

1. make the simulation convenient to run, inspect, visualize, and extend;
2. protect the scientific semantics of an experiment from accidental changes introduced by infrastructure, visualization, or agent implementation details.

The central architectural rule is:

> **There is exactly one authoritative simulation. Everything else observes, drives, records, or analyzes it.**

A headless run and a visual run are not different simulation modes.

Given the same software version, configuration, seed, policies, and external inputs, they must produce the same canonical world-state trajectory.

---

# 1. Architectural status

ECB is being built incrementally.

The architecture distinguishes between components that are already implemented and components that are planned but not yet part of the validated simulation.

## Implemented through M0.2

The current system contains:

- the deterministic M0 simulation kernel;
- typed world, action, observation, and event models;
- explicit simulation configuration;
- controlled random-number streams;
- built-in M0 policies;
- deterministic state hashing;
- reproducible headless experiment execution;
- action logging and replay support;
- run metadata and provenance;
- CSV/JSON/JSONL experiment outputs;
- the first observational baseline-analysis pipeline.

## Target of M1

M1 adds a visual observation layer consisting of:

- an immutable visual snapshot representation;
- a simulation controller independent of the web framework;
- a local visual server;
- a WebSocket protocol;
- a browser client;
- a PixiJS renderer;
- interactive inspection and simulation pacing controls.

M1 must not introduce new scientific mechanics.

In particular, M1 does not add:

- trade;
- communication;
- memory;
- learning;
- reproduction;
- institutions;
- heterogeneous resources;
- new agent privileges;
- new environmental dynamics.

Those belong to later milestones.

---

# 2. Architectural principles

## 2.1 One authoritative world

`WorldState` is the authoritative physical state of an ECB simulation.

Only the simulation kernel may perform canonical transitions of that state.

Policies, runners, analysis tools, servers, renderers, and user interfaces must not mutate the physical world directly.

The dependency direction is:

```text
Policies
   │
   │ Action
   ▼
Simulation Kernel
   │
   │ canonical state transition
   ▼
WorldState
   │
   ├──────────────► Experiment Runner
   │
   ├──────────────► Metrics / Logs / Hashes
   │
   └──────────────► Snapshot Adapter
                         │
                         ▼
                  Visual Controller
                         │
                         ▼
                     WebSocket
                         │
                         ▼
                  Browser / PixiJS
```

The browser is therefore a view of the simulation, not part of the simulation.

---

## 2.2 Scientific mechanics are isolated from presentation

The visual system must not influence:

- agent observations;
- policy decisions;
- random-number generation;
- action resolution;
- metabolism;
- ecology;
- event ordering;
- death;
- world-state hashing.

Changing:

- browser window size;
- rendering frame rate;
- zoom level;
- selected overlay;
- selected agent;
- UI theme;
- WebSocket latency;

must not change the scientific trajectory.

---

## 2.3 Headless execution is canonical

ECB must always remain runnable without:

- a browser;
- a display server;
- JavaScript;
- PixiJS;
- FastAPI;
- WebSockets.

The headless simulation is the canonical experimental execution path.

Visual Mode is an optional observer/controller built on the same kernel.

This protects reproducibility, automated experimentation, CI execution, and future large-scale benchmark runs.

---

## 2.4 Explicit interfaces over hidden coupling

Important boundaries must use explicit data contracts.

Policies receive an `Observation` and return an `Action`.

Visualization receives a `VisualSnapshot`.

Analysis reads recorded experiment artifacts.

The browser communicates with the visual backend through an explicit protocol.

No layer should depend on undocumented internal attributes of another layer.

---

## 2.5 Determinism before convenience

Scientific determinism has priority over UI convenience.

If a feature would make the interface easier to implement but could change simulation ordering, RNG consumption, or physical transitions, that feature must be redesigned.

---

# 3. High-level component model

ECB is divided conceptually into the following layers.

```text
┌───────────────────────────────────────────────┐
│                Experiment Layer               │
│ runner, configurations, metadata, analysis    │
└───────────────────────┬───────────────────────┘
                        │
┌───────────────────────▼───────────────────────┐
│                  Policy Layer                 │
│ Observation → Policy → Action                 │
└───────────────────────┬───────────────────────┘
                        │
┌───────────────────────▼───────────────────────┐
│               Simulation Kernel               │
│ resolution, metabolism, ecology, death        │
└───────────────────────┬───────────────────────┘
                        │
┌───────────────────────▼───────────────────────┐
│              Authoritative State              │
│ WorldState + controlled continuation state    │
└──────────────┬─────────────────────┬──────────┘
               │                     │
               ▼                     ▼
        Logging / Metrics       Snapshot Adapter
                                     │
                                     ▼
                              Visual Controller
                                     │
                                     ▼
                                  Server
                                     │
                                     ▼
                              Browser Client
```

Dependencies should normally point downward or outward from the kernel.

The simulation kernel must never import the browser client or visual server.

---

# 4. Repository organization

The architecture is represented approximately by the following repository structure.

```text
emergent-civilization-benchmark/
│
├── docs/
│   ├── MODEL_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── EMERGENCE_CRITERIA.md
│   ├── METRICS.md
│   └── EXPERIMENTS.md
│
├── experiments/
│   ├── configs/
│   └── m0_baseline/
│       ├── README.md
│       └── analyze.py
│
├── src/
│   └── ecb/
│       ├── model.py
│       ├── config.py
│       ├── rng.py
│       ├── policies.py
│       ├── simulation.py
│       ├── runner.py
│       │
│       └── visual/                 # M1 target
│           ├── snapshot.py
│           ├── controller.py
│           ├── protocol.py
│           └── server.py
│
├── tests/
│
└── visual/                         # M1 browser client
    ├── package.json
    ├── package-lock.json
    ├── index.html
    └── src/
        ├── main.ts
        ├── renderer.ts
        └── ui.ts
```

Exact filenames may evolve during implementation.

The architectural boundaries described in this document are more important than this particular file layout.

---

# 5. Simulation kernel

The simulation kernel is responsible for advancing the scientific world by one canonical tick.

Conceptually:

```text
WorldState(t)
    │
    ├── build observations
    │
    ├── policy decisions
    │
    ├── validate actions
    │
    ├── resolve movement
    │
    ├── resolve harvesting
    │
    ├── apply metabolism
    │
    ├── resolve death
    │
    ├── regenerate ecology
    │
    └── record events / metrics
    ▼
WorldState(t + 1)
```

The detailed scientific ordering is defined by `MODEL_SPEC.md`.

`ARCHITECTURE.md` defines where those rules belong, not what those rules should be.

Changing a scientific transition rule requires an explicit model-specification decision.

It must not occur as a side effect of implementing visualization or infrastructure.

---

# 6. Policy boundary

A policy is an agent decision mechanism.

Its fundamental contract is:

```text
Observation → Action
```

A policy must not receive direct mutable access to `WorldState`.

This is true whether the future policy is:

- scripted;
- heuristic;
- planning-based;
- reinforcement-learned;
- neural;
- LLM-based;
- externally controlled.

Different policy implementations may have very different internal architectures, but they must interact with the world through the same explicit physical interface unless an experiment deliberately specifies otherwise.

This is necessary for meaningful policy comparisons.

---

# 7. Randomness architecture

All scientific randomness must be explicit and controlled.

ECB currently separates random streams so that unrelated stochastic behavior cannot silently perturb other agents.

In particular, policy RNG must not be accidentally coupled through one shared global random stream.

Randomness used by:

- rendering;
- UI animation;
- browser effects;
- visualization sampling;

must never consume simulation RNG.

If the browser requires decorative randomness in the future, that randomness belongs entirely outside the simulation.

---

# 8. State identity and hashing

ECB distinguishes two important concepts.

## 8.1 World-state hash

`world_state_hash` identifies the canonical physical scientific state.

It covers physical simulation information such as:

- tick;
- agents;
- positions;
- health;
- inventories;
- productivity;
- environmental resource stocks.

It intentionally excludes non-physical infrastructure state such as:

- rendering state;
- UI state;
- event-display history;
- browser state.

The world-state hash is the primary invariant for comparing physical trajectories.

---

## 8.2 Execution-state hash

`execution_state_hash` represents continuation-equivalent simulation state.

In addition to the physical world, it includes future-relevant controlled state such as:

- configuration;
- RNG state;
- policy identity;
- policy configuration;
- declared continuation-relevant policy state.

Two equal world-state hashes do not necessarily imply identical future continuation.

Two equal execution-state hashes under the same software and future external inputs are intended to represent deterministic continuation equivalence.

---

## 8.3 Visualization exclusion

Visual state must never contribute to either scientific hash.

The following must therefore remain hash-irrelevant:

```text
camera position
zoom
selected overlay
selected agent
browser dimensions
render frame count
WebSocket packet count
UI playback speed
```

Playback speed affects only when ticks occur in wall-clock time.

It does not change what a tick means.

---

# 9. Headless experiment runner

The headless runner is responsible for reproducibly executing experiments around the kernel.

Its responsibilities include:

- constructing a simulation from explicit configuration;
- assigning policies;
- advancing ticks;
- collecting metrics;
- recording actions;
- recording events;
- recording provenance;
- writing deterministic experiment artifacts;
- terminating on the specified experimental condition.

The runner does not own alternative simulation mechanics.

It invokes the same kernel used elsewhere.

Current run artifacts include:

```text
metadata.json
metrics.csv
events.jsonl
actions.jsonl
```

Raw experimental data is separated from derived analysis output.

---

# 10. Experiment provenance

Scientific results must remain attributable to the exact experiment that produced them.

Run metadata therefore records information such as:

- simulation configuration;
- root seed;
- requested duration;
- policy identity;
- policy configuration;
- source/software identity;
- initial and final state identity where applicable.

Analysis code must validate provenance rather than infer it from filenames.

For example:

```text
runs/m0/oracle_seed_0/
```

is a convenient directory name.

It is not scientific proof that the contained run actually used Oracle policy with seed 0.

The authoritative evidence is the recorded metadata.

---

# 11. Analysis layer

Scientific analysis is downstream of recorded experiment artifacts.

Analysis code must not mutate or resume the simulation merely to interpret an existing run.

The dependency direction is:

```text
Simulation
    ▼
Recorded Run
    ▼
Analysis
    ▼
Derived Results
```

M0.2 establishes this pattern.

Derived artifacts such as plots and regenerated summaries may remain ignored when they can be deterministically reconstructed from validated raw experiment data.

Scientific interpretation belongs in version-controlled experiment documentation.

---

# 12. M1 Visual Mode

M1 introduces a real-time visual representation of ECB.

The fundamental rule is:

> **Visual Mode is a view of an ECB experiment, not a different ECB experiment.**

For identical scientific inputs:

```text
same software
+ same configuration
+ same seed
+ same policies
+ same external inputs
```

the physical trajectory must remain identical whether visualization is active or not.

---

# 13. Visual architecture

The M1 data path is:

```text
                ┌────────────────────┐
                │ Simulation Kernel  │
                └─────────┬──────────┘
                          │
                          │ WorldState
                          ▼
                ┌────────────────────┐
                │ Snapshot Adapter   │
                └─────────┬──────────┘
                          │
                          │ VisualSnapshot
                          ▼
                ┌────────────────────┐
                │ Visual Controller  │
                └─────────┬──────────┘
                          │
                          │ serialized snapshot
                          ▼
                ┌────────────────────┐
                │ FastAPI/WebSocket  │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Browser / PixiJS   │
                └────────────────────┘
```

Each component has a deliberately narrow responsibility.

---

# 14. Snapshot adapter

The browser must not receive `WorldState` directly.

M1 introduces an explicit immutable, JSON-serializable `VisualSnapshot`.

The snapshot is a projection of authoritative state intended only for observation.

A conceptual M1 snapshot is:

```text
VisualSnapshot
│
├── tick
├── world_state_hash
│
├── world
│   ├── width
│   └── height
│
├── agents[]
│   ├── id
│   ├── x
│   ├── y
│   ├── alive
│   ├── health
│   ├── food
│   └── water
│
├── cells[]
│   ├── x
│   ├── y
│   ├── food
│   └── water
│
├── metrics
│   ├── alive_agents
│   ├── mean_health_alive
│   ├── total_world_food
│   └── total_world_water
│
└── recent_events[]
```

The exact serialized schema will be finalized during implementation and tested explicitly.

---

# 15. Snapshot constraints

A visual snapshot must satisfy the following properties.

### Read-only semantics

Creating or consuming a snapshot must not modify the simulation.

### Deterministic projection

Given the same authoritative state, snapshot generation must produce semantically identical output.

### No hidden simulation authority

A snapshot must not expose mutable references into the live world.

### No unnecessary continuation state

M1 snapshots do not need:

- RNG internals;
- complete policy internals;
- execution-state restoration data;
- server internals.

### Explicit coordinate convention

Coordinates exposed to the browser must use the same canonical coordinate convention documented for the simulation.

Rendering code may transform those coordinates into pixels but must not redefine their scientific meaning.

---

# 16. Full snapshots before deltas

M1 intentionally begins with complete snapshots.

The default M0 world contains:

```text
64 × 64 = 4096 cells
256 initial agents
```

At this scale, architectural simplicity is more valuable than premature network optimization.

Therefore M1 should first send sufficient state for the client to reconstruct the entire visible world from a single snapshot.

Incremental/delta protocols may be considered later only if measurement shows that full snapshots are an actual bottleneck.

Correctness comes before transport optimization.

---

# 17. Visual controller

The `VisualController` is the architectural boundary between simulation execution and the web server.

It must be usable and testable without:

- FastAPI;
- a browser;
- WebSocket transport;
- PixiJS.

Conceptually it owns operations such as:

```text
current_snapshot()
step()
play()
pause()
set_speed(...)
```

The controller invokes the canonical simulation step.

It does not reimplement simulation rules.

This separation is important because otherwise scientific behavior could become entangled with HTTP/WebSocket lifecycle behavior.

---

# 18. Simulation time versus wall-clock time

ECB simulation time is tick-based.

Wall-clock time is presentation infrastructure.

This distinction is strict.

If the simulation executes:

```text
tick 100
tick 101
tick 102
tick 103
```

all four scientific transitions occurred regardless of how many frames the browser rendered.

At high execution speed the browser may display:

```text
100 → 102 → 103
```

This is acceptable.

The missing rendered frame does not represent a missing simulation tick.

---

# 19. Rendering may skip frames; simulation may not skip ticks

This is a core M1 invariant.

Suppose the simulator can execute faster than the browser can draw.

The architecture should prefer:

```text
simulate every canonical tick
publish/render selected recent snapshots
```

rather than:

```text
skip simulation work because rendering is behind
```

Rendering is lossy with respect to wall-clock presentation.

Simulation is lossless with respect to canonical tick transitions.

---

# 20. Playback controls

M1 targets the following controls:

```text
Pause
Play
Step
1x
5x
20x
Max
```

Their semantics are infrastructural.

## Pause

Stops automatic advancement.

It does not alter simulation state.

## Play

Allows automatic canonical stepping according to the selected wall-clock pacing.

## Step

Executes exactly one canonical simulation tick.

## 1x / 5x / 20x

Change target wall-clock pacing.

They do not modify:

- metabolism;
- regeneration;
- policy frequency;
- physical time represented by one tick.

## Max

Advances the canonical simulation as quickly as practical while allowing the visualization layer to publish useful snapshots without requiring one rendered frame per simulated tick.

---

# 21. M1 scheduling

The scheduler/controller must preserve deterministic simulation ordering independently of rendering latency.

Network or browser latency must not enter the scientific model.

A slow browser may cause:

- fewer displayed snapshots;
- older snapshots to be discarded;
- visual latency.

It must not cause:

- different actions;
- reordered ticks;
- changed RNG consumption;
- different physical states.

---

# 22. Backpressure strategy

M1 should prefer freshness over accumulating an unbounded visualization queue.

If simulation advances faster than the browser consumes snapshots, it is normally better for the visual layer to display the newest available complete snapshot than to render every stale intermediate state.

Because snapshots are observational, discarding an unrendered snapshot is safe.

Discarding a simulation tick is not.

The visual transport queue must therefore remain logically separate from the simulation transition sequence.

---

# 23. Visual server

The target M1 backend uses:

```text
FastAPI
WebSocket
Uvicorn
```

The server is responsible for transport and lifecycle management.

It may:

- serve the visual client;
- establish WebSocket connections;
- receive valid UI control messages;
- publish snapshots;
- expose basic session status.

It must not:

- resolve movement;
- run metabolism;
- regenerate resources;
- decide policies;
- mutate agent inventories itself;
- implement an alternative tick loop with different scientific semantics.

Those responsibilities belong to the simulation/controller layers.

---

# 24. Browser protocol

Client/server communication must use explicit message types.

Conceptually, server-to-client messages may include:

```text
snapshot
status
error
```

Client-to-server messages may include:

```text
pause
play
step
set_speed
inspect
```

The exact M1 protocol should be small and versionable.

Unknown or malformed messages should fail clearly rather than causing implicit simulation behavior.

Scientific configuration changes should not be smuggled into generic UI commands.

---

# 25. Browser authority

The browser has no authority over physical world state.

The browser may request operations such as:

```text
step the simulation
pause automatic stepping
resume automatic stepping
change wall-clock speed
inspect an entity
```

It may not send commands such as:

```text
set agent health to 100
move agent to x=4,y=9
give agent food
change cell resources
revive agent
```

unless a future explicitly specified experimental/debugging interface is designed for that purpose.

Such mutations are outside M1.

---

# 26. Visual client

The M1 browser client is expected to use:

```text
TypeScript
Vite
PixiJS
```

PixiJS provides a rendering model suitable for large numbers of cells and agents without representing every visual element as a DOM node.

The client owns presentation state such as:

- camera;
- zoom;
- selected overlay;
- selected agent;
- panel visibility.

This client state is not scientific state.

---

# 27. M1 world rendering

The first visual implementation should represent the real M0 state rather than inventing decorative world features.

The renderer should support the 64 × 64 world and expose at least these conceptual layers:

```text
Agents
Food
Water
Health
Density
```

The UI may transform scientific values into visual intensity or symbols.

Such visual mappings must not modify the underlying values.

---

# 28. Agent rendering

Multiple agents may occupy one cell.

The renderer must therefore not assume:

```text
one cell = one agent
```

Visual representation of multi-occupancy is a presentation problem.

Possible rendering techniques may evolve, but the renderer must preserve the fact that co-located agents remain distinct simulation entities.

The UI must not accidentally imply collision or territorial exclusion that does not exist in M0.

---

# 29. Resource overlays

Food and water overlays visualize actual cell stocks.

They should use the physical resource values supplied by the snapshot.

Any normalization used for display must be a renderer concern.

For example, color intensity may be normalized relative to resource capacity.

This normalization must never feed back into the simulation.

---

# 30. Health and density overlays

A health overlay may summarize agent health spatially.

A density overlay may summarize occupancy.

If multiple agents occupy a cell, aggregation rules used only for visualization must be explicit.

These derived visual values are not new simulation variables.

---

# 31. Agent inspection

M1 should allow selecting an agent for inspection.

The initial detail panel may expose:

```text
agent ID
position
alive/dead state
health
food inventory
water inventory
```

Inspection is read-only.

Selecting an agent must not change its observation, policy, or future trajectory.

---

# 32. Event feed

M1 may expose a lightweight recent-event feed.

It is intended as a debugging and observation aid.

The event feed should derive from canonical simulation events.

The UI must not create synthetic scientific events merely for animation purposes and then mix them with actual simulation events.

Presentation-only notifications must remain distinguishable from simulation events.

---

# 33. Live metrics

M1 may display lightweight aggregate metrics such as:

```text
current tick
alive population
mean health of living agents
total world food
total world water
```

These values should be derived from the same authoritative state semantics used by headless measurement.

Visual metrics must not silently introduce alternative definitions for metrics that already exist in the runner.

---

# 34. No analytical dashboard in M1.0

M1.0 is primarily a microscope for the current world.

Complex temporal scientific analysis remains the responsibility of experiment-analysis tooling.

The first UI therefore does not need to reproduce the complete M0.2 analysis pipeline.

This avoids coupling exploratory visualization to scientific statistical analysis prematurely.

Later versions may display selected historical charts if they can do so without becoming the authoritative analysis path.

---

# 35. Visual equivalence invariant

The most important M1 correctness property is trajectory equivalence.

For a fixed experiment:

```text
configuration = C
seed = S
policy assignment = P
ticks = N
```

a headless execution may produce:

```text
H0, H1, H2, ..., HN
```

where each `H` is a `world_state_hash`.

Running the same experiment through the visual controller must produce:

```text
H0, H1, H2, ..., HN
```

with exact tick-by-tick equality.

Rendering frames are irrelevant to this comparison.

If this invariant fails, M1 is not scientifically transparent and the discrepancy is a blocking bug.

---

# 36. Required M1 tests

The implementation should include focused tests around the architectural boundaries.

At minimum, M1 should verify:

- snapshot creation does not mutate the world;
- snapshot contents correspond to authoritative state;
- snapshot serialization is deterministic;
- multi-agent cell occupancy is represented correctly;
- pause does not advance ticks;
- step advances exactly one tick;
- playback speed does not alter simulation semantics;
- visual-controller stepping matches direct/headless stepping;
- world-state hashes match tick by tick;
- malformed control messages are rejected;
- visual transport does not consume simulation RNG.

Tests of the controller should not require launching a real browser.

Browser-specific tests may be added separately where useful.

---

# 37. M1 startup model

The first version should prefer explicit startup configuration over building a complex experiment-configuration UI.

A target invocation may resemble:

```bash
ecb-visual --policy oracle --seed 0
```

or an equivalent module entry point.

The exact CLI name is an implementation decision.

The important architectural property is that scientific startup parameters remain explicit and reproducible.

A later version may provide a richer launcher UI.

---

# 38. Local-first server

M1 is primarily a local research/development tool.

The initial visual server should therefore default to a local interface rather than exposing the simulation publicly.

Remote hosting, authentication, multi-user sessions, and internet deployment are outside the initial M1 requirement.

They should not complicate the first scientific visualization implementation.

---

# 39. Performance target

ECB development currently targets commodity developer hardware, including Apple Silicon laptops.

M1 should therefore avoid obviously unnecessary per-frame work.

However, performance optimization must be evidence-driven.

The preferred order is:

```text
correctness
→ deterministic equivalence
→ usable visualization
→ profiling
→ optimization
```

not:

```text
complex optimization
→ uncertain semantics
→ later correctness repair
```

---

# 40. Visual performance versus simulation performance

Rendering and simulation performance must be measured separately.

A slow browser does not necessarily imply a slow simulation.

A slow simulation does not necessarily imply a slow renderer.

Future profiling should therefore distinguish at least:

```text
simulation ticks / second
snapshot construction cost
snapshot serialization cost
transport rate
browser render frames / second
```

This separation will make later optimization more informative.

---

# 41. Failure behavior

Architectural failures should be explicit.

Examples include:

- malformed snapshot data;
- invalid control messages;
- disconnected clients;
- missing frontend assets;
- invalid startup configuration.

A visualization failure should not silently alter scientific simulation state.

Where practical, server or client failure should either leave the simulation safely paused/stopped or terminate the visual session clearly.

---

# 42. Future LLM policies

Real LLM agents are a future policy implementation, not a different physical universe.

They should eventually act through the same policy boundary:

```text
Observation → Policy → Action
```

An LLM policy may internally use a slower hierarchical design.

For example:

```text
Observation
    ▼
LLM deliberation every N ticks or on important events
    ▼
temporary intention / plan
    ▼
local controller
    ▼
primitive ECB Action
```

This can reduce API cost and latency while preserving the same physical action interface.

---

# 43. Simulation time and future LLM latency

Future API latency must not redefine canonical simulation time.

If an LLM takes several wall-clock seconds to produce a decision, this does not imply that several ECB ticks have passed.

Canonical simulation time remains controlled by the experiment.

Any future asynchronous real-time execution mode must be explicitly defined as a different experimental scheduling regime rather than silently changing the tick semantics of the canonical benchmark.

---

# 44. Future communication architecture

Communication is not implemented in M0 or M1.

When introduced, it should remain compatible with heterogeneous policy types.

Future layers may include:

```text
structured protocol
symbolic communication
natural-language communication
```

A structured protocol allows scripted, planning, RL, and LLM agents to interact without requiring every participant to invoke a language model.

Symbolic communication may allow agents to assign meaning to initially uninterpreted tokens.

Natural-language communication may be available to policies capable of using it.

Communication mechanics must be specified scientifically before implementation.

---

# 45. Future framework integration

ECB may integrate external agent-simulation frameworks where they provide clear value.

The expected direction is to evaluate/use Mesa 3.x for broader agent-based-model infrastructure after the framework-independent deterministic kernel is stable.

PettingZoo adapters may later expose ECB to reinforcement-learning ecosystems.

These integrations must wrap or interface with explicitly specified ECB semantics rather than silently replacing them.

External framework lifecycle conventions must not become accidental scientific rules.

---

# 46. Separation of imposed and emergent structure

Architecture must help preserve the distinction between:

```text
world rules
agent capabilities
agent policy
derived metrics
observed phenomena
```

For example, if a future experiment studies leadership, the architecture should not require a built-in `leader` flag merely because the UI wants to draw leaders differently.

If leadership is intended to emerge, visualization should derive its representation from an explicitly defined metric or analysis rather than inject the phenomenon into the state model.

The same principle applies to:

- professions;
- communities;
- markets;
- settlements;
- hierarchy;
- reputation;
- institutions.

---

# 47. Observability is not ontology

A value being useful to display does not automatically justify adding it to `WorldState`.

This is an important architectural discipline.

The UI may want concepts such as:

```text
resource pressure
local density
trade centrality
community membership
influence
```

Some of these may be derived from existing state or experiment history.

They should remain derived observables unless the scientific model explicitly requires agents or world mechanics to possess them as causal state variables.

---

# 48. Architectural change discipline

Changes that affect only:

```text
rendering
UI layout
transport
analysis presentation
developer tooling
```

normally belong to architecture/infrastructure.

Changes that affect:

```text
what an agent observes
what actions exist
how actions resolve
resource dynamics
health dynamics
agent capabilities
random scientific transitions
```

are model changes.

Model changes require explicit specification and corresponding tests.

They must not be hidden inside infrastructure pull requests.

---

# 49. Dependency rule

The desired dependency direction can be summarized as:

```text
MODEL SPECIFICATION
        │
        ▼
CORE MODELS / CONFIG / RNG
        │
        ▼
SIMULATION KERNEL
      ╱     ╲
     ▼       ▼
 POLICIES   OBSERVERS
             │
       ┌─────┴─────┐
       ▼           ▼
    RUNNER      SNAPSHOTS
       │           │
       ▼           ▼
   RUN DATA     CONTROLLER
       │           │
       ▼           ▼
   ANALYSIS      SERVER
                   │
                   ▼
                 CLIENT
```

Lower-level scientific modules must not depend on higher-level presentation modules.

In particular:

```text
simulation.py
```

must not import from:

```text
visual/
FastAPI
WebSocket
PixiJS
experiment analysis code
```

---

# 50. M1 acceptance criteria

M1 Visual Mode is considered architecturally successful when all of the following are true:

1. a real M0 simulation can be observed in a browser;
2. Play, Pause, Step, and speed controls work;
3. the 64 × 64 world can be inspected through the required overlays;
4. agents and multi-occupancy are represented correctly;
5. an individual agent can be inspected without affecting it;
6. current metrics and recent canonical events are visible;
7. the browser never mutates `WorldState`;
8. the visual controller can be tested independently of the web server;
9. full snapshots are sufficient for M1 correctness;
10. visual and headless executions produce identical `world_state_hash` trajectories for equivalent experiments;
11. visualization does not consume scientific RNG;
12. all existing M0/M0.1/M0.2 tests remain valid.

If visual equivalence fails, M1 is not complete even if the interface appears to work.

---

# 51. Architectural north star

ECB should remain capable of evolving from:

```text
simple deterministic agents
```

through:

```text
heterogeneous agents
→ trade
→ memory
→ communication
→ learning
→ institutions
→ LLM agents
```

without replacing the foundational experimental architecture each time.

The long-term objective is to make very different forms of intelligence inhabit the same explicitly specified world while preserving reproducibility and meaningful comparison.

The architectural north star is therefore:

> **One world, explicit rules, interchangeable minds, reproducible experiments, and observers that never become hidden causes.**
