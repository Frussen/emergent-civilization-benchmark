# ECB Emergence Criteria

## Emergent Civilization Benchmark

This document defines the methodological criteria ECB uses before describing an observed pattern as **emergent**.

ECB is designed to study artificial societies in which potentially interesting structures arise from local agent behavior and explicit world rules.

That goal creates a major scientific risk:

> A visually interesting pattern can be mistaken for emergence even when it is directly caused by the model designer, a deterministic policy convention, a hidden variable, a measurement artifact, or an implementation detail.

The purpose of this document is to make that mistake difficult.

The central rule is:

> **Emergence is an empirical claim, not a visual impression.**

A phenomenon should be called emergent only when ECB can show that the phenomenon was not directly encoded as the target structure, can be measured independently of the claim, persists beyond a transient coincidence, appears robustly across appropriate replications, and survives relevant controls or ablations.

---

# 1. Status

This document defines the methodological standard that future ECB experiments should follow.

It does not claim that M0 or M1 already contain emergent civilization.

Through M0.2, ECB has demonstrated infrastructure and viability properties only.

In particular, the confirmed period-2 Oracle synchronization observed in the M0 baseline is **not** classified as emergent social behavior.

It is consistent with symmetric world rules and deterministic policy structure and therefore serves as a useful negative example for this document.

M1 Visual Mode adds observability, not new social mechanics.

---

# 2. What ECB means by emergence

For ECB, a phenomenon is a candidate emergent phenomenon when:

1. it is not directly specified as the target macrostructure;
2. it arises from interactions among lower-level rules, agent policies, environmental constraints, and history;
3. it can be operationally measured;
4. it is not adequately explained by a trivial implementation artifact or deterministic convention;
5. it shows appropriate persistence, recurrence, or structural stability;
6. it survives relevant comparison against null models or controls;
7. it is reproducible across an appropriate set of seeds or experimental replications;
8. plausible causal mechanisms can be probed through ablation or controlled variation.

This definition is intentionally stricter than:

> "Something unexpected appeared."

Unexpectedness may motivate investigation.

It is not sufficient evidence of emergence.

---

# 3. Five categories that must remain distinct

Every ECB analysis should distinguish the following categories.

```text
WORLD RULES
    ↓
AGENT CAPABILITIES
    ↓
AGENT POLICY
    ↓
OBSERVED / DERIVED METRICS
    ↓
CANDIDATE PHENOMENA
```

These categories must not be collapsed.

## 3.1 World rules

World rules define the physical and institutional possibilities explicitly imposed by the model.

Examples include:

- movement rules;
- resource regeneration;
- metabolism;
- action resolution;
- communication channels;
- trade mechanics;
- memory availability;
- observation radius.

These are not emergent.

They are experimental conditions.

---

## 3.2 Agent capabilities

Capabilities define what an agent is physically or informationally able to do.

Examples include:

- move;
- harvest;
- communicate;
- trade;
- remember;
- inspect local observations;
- make offers;
- form contracts if such an action exists.

Capabilities are not themselves evidence that the corresponding social structure emerged.

For example:

> Allowing agents to trade does not mean a market emerged.

---

## 3.3 Agent policy

A policy determines how an agent chooses actions within its allowed interface.

Examples include:

- RandomPolicy;
- survival heuristic;
- planning agent;
- RL agent;
- LLM agent.

A behavior explicitly hard-coded into a policy must not later be presented as emergent.

If a policy contains:

```text
if hungry:
    harvest food
```

then food-seeking behavior is policy logic.

It is not an emergent discovery.

---

## 3.4 Derived metrics

Metrics are measurements computed from the world, actions, events, or interaction history.

Examples include:

- trade volume;
- degree centrality;
- spatial clustering;
- resource inequality;
- persistence of interaction partners;
- specialization indices.

A metric may reveal a phenomenon.

The metric is not itself a new causal variable unless the model explicitly makes it one.

---

## 3.5 Candidate phenomena

Candidate phenomena are higher-level structures inferred from lower-level behavior.

Examples may eventually include:

- division of labor;
- exchange networks;
- persistent settlements;
- social hierarchy;
- communities;
- reputational structure;
- institutions;
- norms;
- coordination conventions.

These require evidence.

They must not be assumed merely because the simulation includes variables with similar names.

---

# 4. Observability is not ontology

A concept being useful to visualize or measure does not automatically justify adding it to the authoritative world state.

For example, future analysis may compute:

```text
community membership
influence
market centrality
social rank
settlement density
specialization score
```

These should remain derived quantities unless the scientific model explicitly requires them as causal state variables.

This prevents the benchmark from accidentally creating the phenomenon it later claims to observe.

A visualization may color an agent as a "high-centrality trader."

That does not mean the world contains a built-in `high_centrality_trader = true` state.

---

# 5. No direct encoding of the claimed macrostructure

The strongest anti-circularity rule in ECB is:

> **Do not directly encode the structure that an experiment is intended to discover.**

If an experiment claims to investigate whether leadership emerges, it should not begin by assigning a privileged `leader` role unless leadership assignment itself is the treatment being studied.

If an experiment claims to investigate specialization, it should not directly assign permanent professions unless the experiment explicitly studies the consequences of imposed professions.

The same rule applies to all future social claims.

---

# 6. Examples of prohibited circular shortcuts

The following are examples of implementations that would undermine a later emergence claim.

## Leadership

Bad design for an emergence experiment:

```text
agent.role = "leader"
leader_bonus = +50% influence
```

Then observing one agent dominate decisions would not demonstrate emergent leadership.

---

## Professions

Bad design:

```text
agent.profession = "farmer"
agent.profession = "trader"
```

Then measuring occupational specialization would mostly measure an imposed label.

---

## Communities

Bad design:

```text
agent.group_id = 3
```

Then later "discovering" three communities from that same group assignment would be circular.

---

## Markets

Bad design:

```text
global_market_price = ...
```

if the scientific question is whether decentralized exchange generates price-like coordination.

A global market-clearing mechanism would already impose much of the macrostructure.

---

## Reputation

Bad design:

```text
universal_reputation_score[agent]
```

if the experiment asks whether agents develop social reputation from experience.

A globally correct score would pre-solve the information problem.

---

## Settlements

Bad design:

```text
village_zone = true
```

if the experiment asks whether persistent settlements form.

---

## Hierarchy

Bad design:

```text
power_level = fixed_rank
```

if the experiment asks whether hierarchical power distribution emerges from interaction.

---

# 7. Allowed primitives versus forbidden conclusions

ECB may need low-level primitives that make a phenomenon physically possible.

This is not the same as encoding the phenomenon.

For example:

| Candidate phenomenon | Low-level primitives that may be allowed | Structure that should not be pre-installed |
|---|---|---|
| Division of labor | heterogeneous skills, resources, exchange | fixed professions |
| Market-like exchange | bilateral offers, transfer actions | global price or auctioneer unless treatment requires it |
| Reputation | memory of interactions, messages | universal true reputation score |
| Communities | repeated interaction, communication graph | fixed social group IDs |
| Hierarchy | unequal outcomes, delegation mechanisms | leader flag or rank bonus |
| Settlements | movement, local resources, construction if specified | pre-labelled village zones |
| Norms | communication, memory, enforcement actions | hard-coded norm labels |
| Institutions | repeated interaction, voting/contract primitives if specified | pre-scripted institution outcome |

The scientific question is often whether local primitives are sufficient for macrostructure to arise.

---

# 8. Claim ladder

ECB should use graded language rather than jumping directly from observation to "emergence."

## Level 0 — Raw observation

Example:

> Agent density increased near a subset of resource-rich cells.

This is descriptive only.

---

## Level 1 — Recurrent pattern

Example:

> Spatial clustering appeared in 18 of 20 runs and persisted for more than 500 ticks.

This establishes recurrence and persistence.

It still does not establish mechanism.

---

## Level 2 — Candidate emergent phenomenon

Example:

> Persistent spatial clusters arose without explicit settlement labels and were absent in the matched random-policy control.

This is stronger because a direct encoding and a simple null explanation have been addressed.

---

## Level 3 — Robust emergent phenomenon

Example:

> Persistent spatial clusters arise across seeds and moderate parameter variation, disappear under targeted ablation of the suspected mechanism, and reappear when that mechanism is restored.

This supports a causal interpretation.

---

## Level 4 — Generalized phenomenon

Example:

> Similar settlement-like organization appears across multiple policy families, ecological regimes, and population sizes under the same operational criterion.

This supports broader generality beyond one narrow configuration.

ECB should reserve its strongest terminology for claims near Levels 3–4.

---

# 9. Operational definition required before strong claims

Before a major experiment is interpreted, the target phenomenon should have an operational definition.

A useful operational definition specifies:

1. the observable variables;
2. the metric or detection procedure;
3. a threshold or comparison rule;
4. the minimum persistence duration;
5. the replication requirement;
6. the null/control condition;
7. the expected falsification condition.

For example, "settlement" should not mean:

> A cluster that looks village-like on the screen.

It should mean something measurable, such as a persistent spatial concentration meeting a predefined density and duration criterion.

The exact definition should be fixed before inspecting the final treatment results whenever practical.

---

# 10. Persistence requirement

A transient fluctuation is not enough for most civilization-level claims.

ECB should therefore distinguish:

```text
momentary pattern
temporary regime
persistent structure
```

The required persistence horizon depends on the phenomenon.

Examples:

- a temporary queue at a resource node may require only a short window;
- a settlement should persist for substantially longer;
- an institution should survive repeated opportunities for violation or turnover;
- a hierarchy should remain identifiable across multiple interactions.

The persistence criterion should be stated explicitly in the experiment design.

---

# 11. Replication across seeds

Single-seed discoveries are exploratory.

They are not strong evidence of robust emergence.

Experiments claiming emergence should normally evaluate multiple controlled seeds.

Seed count should be appropriate to:

- variance of the phenomenon;
- computational cost;
- effect size;
- strength of the claim.

ECB should report:

- number of seeds;
- fraction of runs meeting the criterion;
- between-seed variability;
- failures as well as successes.

Runs that do not exhibit the phenomenon must not be silently discarded.

---

# 12. Null models and controls

A candidate emergent pattern should be compared against an appropriate null or control whenever possible.

Possible controls include:

- random policy;
- memoryless policy;
- shuffled interaction partners;
- disabled communication;
- disabled trade;
- homogeneous productivity;
- randomized spatial positions;
- alternative deterministic tie-breaking;
- equivalent environment without the suspected interaction mechanism.

The purpose of a null model is not merely to produce worse performance.

It is to test whether the proposed mechanism is necessary to explain the measured structure.

---

# 13. Ablation

Ablation is one of ECB's main tools for distinguishing genuine mechanism from coincidence.

An ablation deliberately removes or alters one component while keeping the rest of the experiment as comparable as possible.

Examples:

```text
full model
→ remove communication
→ remove memory
→ remove trade
→ randomize productivity
→ remove reputation information
```

If the target phenomenon disappears specifically when a suspected mechanism is removed, causal confidence increases.

If the phenomenon remains unchanged, the proposed explanation is weakened.

Ablation results should include negative findings.

---

# 14. Symmetry-breaking tests

Highly symmetric worlds can produce synchronized patterns without social coordination.

M0.2 demonstrates this risk.

The Oracle baseline shows an exact aggregate period-2 cycle under symmetric:

- food and water needs;
- initial inventories;
- productivity;
- resource environment;
- deterministic policy behavior;
- food-first tie-breaking.

Therefore, whenever a striking synchronized pattern appears, ECB should ask:

> Does the pattern survive if irrelevant symmetries are broken?

Useful symmetry-breaking interventions may include:

- heterogeneous initial inventories;
- heterogeneous productivity;
- spatial resource heterogeneity;
- randomized tie-breaking where scientifically justified;
- asynchronous policy phases if explicitly specified;
- small perturbations to initial conditions.

A pattern that disappears immediately under arbitrary symmetry breaking may be a model artifact rather than a robust social phenomenon.

---

# 15. Policy-induced versus interaction-induced structure

ECB should distinguish structure generated by:

```text
one agent responding to its own state
```

from structure generated by:

```text
agents responding to one another
```

A population of identical deterministic policies may exhibit synchronized aggregate behavior even if agents never communicate or influence one another.

Such synchronization can be interesting.

It should not automatically be called social emergence.

Evidence for social emergence should demonstrate that inter-agent interaction materially contributes to the phenomenon.

---

# 16. Environment-induced structure

Environmental geometry can also create apparent organization.

For example:

```text
resource hotspot
→ agents gather there
→ visible cluster
```

The resulting cluster may be a straightforward response to geography rather than a socially maintained settlement.

To distinguish these explanations, future experiments may compare:

- static resource hotspots;
- moving resources;
- homogeneous environments;
- environments after resource depletion;
- persistence after the original environmental attractor disappears.

The correct conclusion may still be that a settlement-like pattern emerged, but the environmental contribution must be quantified rather than ignored.

---

# 17. Measurement artifacts

A candidate phenomenon may also be created by the measurement procedure.

Examples include:

- arbitrary clustering thresholds;
- smoothing windows;
- bin sizes;
- graph-community algorithm resolution;
- visualization normalization;
- truncated event history.

ECB analyses should therefore document:

- metric definitions;
- thresholds;
- windows;
- normalization;
- algorithm parameters.

When reasonable, results should be tested for sensitivity to these choices.

---

# 18. Visualization is exploratory evidence, not final evidence

Visual Mode is intended to help researchers notice patterns.

It is not itself the scientific validation layer.

The workflow should be:

```text
visual observation
        ↓
candidate hypothesis
        ↓
operational metric
        ↓
controlled experiment
        ↓
replication
        ↓
ablation / null comparison
        ↓
scientific claim
```

A compelling animation may motivate an experiment.

It must not replace one.

---

# 19. Pre-registration mindset

ECB does not require formal external preregistration for every exploratory run.

However, for strong claims it should adopt a preregistration mindset:

Before running the final confirmatory experiment, specify:

- target phenomenon;
- metric;
- thresholds;
- treatment;
- controls;
- seed set or sampling rule;
- stopping condition;
- expected analysis.

Exploratory and confirmatory analyses should be distinguished in documentation.

This reduces accidental cherry-picking.

---

# 20. Multiple-comparison discipline

As ECB becomes richer, many metrics will be observable simultaneously.

This creates a risk:

> If enough statistics are inspected, something unusual will eventually appear by chance.

Therefore strong claims should avoid selecting a metric only because it looked interesting after examining many alternatives.

If a pattern is discovered exploratorily, it should ideally be tested again on:

- fresh seeds;
- held-out configurations;
- a newly specified confirmatory experiment.

---

# 21. Survival is not emergence

An agent or society surviving for a long time is not by itself an emergent phenomenon.

M0 deliberately establishes this distinction.

Survival may be:

- a viability property;
- a policy-performance metric;
- a prerequisite for later social behavior.

It is not automatically evidence of:

- intelligence;
- cooperation;
- institutions;
- civilization.

---

# 22. Performance is not emergence

A policy outperforming another policy does not imply emergence.

For example:

```text
OracleSurvivalPolicy > RandomPolicy
```

demonstrates policy-sensitive viability.

It does not demonstrate an emergent institution or collective intelligence.

ECB must separate:

```text
individual competence
collective performance
social structure
emergent structure
```

These may correlate in future experiments, but they are not synonymous.

---

# 23. Complexity is not emergence

A complicated trajectory is not necessarily emergent.

Complexity may result from:

- random noise;
- chaotic sensitivity;
- large state spaces;
- policy complexity;
- visualization clutter.

A useful emergence claim requires identifiable macrostructure, not merely difficulty of prediction.

---

# 24. Surprise is not emergence

A result can surprise the researchers while being directly implied by imposed rules.

The M0 period-2 Oracle cycle is again a useful example.

It was initially interesting because the exact aggregate difference was unexpected.

Temporal analysis then showed a deterministic cycle consistent with model symmetry.

The appropriate scientific response is not:

> We discovered emergent synchronization.

It is:

> We found a reproducible synchronized pattern and identified a plausible imposed-rule explanation requiring targeted ablation for causal confirmation.

This is the standard ECB should maintain.

---

# 25. Candidate phenomenon template

Each future emergence claim should be documented in a structure similar to the following.

```text
Phenomenon:
Operational definition:
Relevant world rules:
Relevant agent capabilities:
Relevant policy assumptions:

Primary metric:
Persistence threshold:
Replication requirement:

Null/control:
Ablations:
Symmetry-breaking tests:

Observed result:
Seeds exhibiting criterion:
Effect size / strength:
Failure cases:

Alternative explanations:
Evidence against alternatives:

Claim level:
Remaining uncertainty:
```

This template should be adapted to the phenomenon rather than followed mechanically.

---

# 26. Division of labor

A future claim of division of labor should not rely merely on heterogeneous productivity.

Heterogeneous productivity is an imposed capability difference.

Evidence of emergent division of labor would instead involve agents behaviorally specializing over time.

Possible future measurements may include:

- action specialization;
- production specialization;
- persistent role differentiation;
- complementary exchange;
- increased specialization relative to a no-trade or randomized control.

The design should not require agents to possess fixed profession labels.

---

# 27. Market-like organization

A future market claim should distinguish:

```text
trade occurred
```

from:

```text
market-like coordination emerged
```

Bilateral exchange alone demonstrates trade activity.

Stronger market-like organization may involve measurable features such as:

- repeated exchange;
- price convergence;
- stable exchange ratios;
- liquidity;
- specialization linked to exchange;
- decentralized coordination.

If a global clearing price or centralized auctioneer is imposed, those mechanisms must be treated as world rules rather than emergent properties.

---

# 28. Reputation

A future reputation claim should require more than stored interaction history.

Memory is a capability.

Reputation requires that information about past behavior affects future social treatment in a persistent and structured way.

Possible evidence may include:

- partner selection based on prior behavior;
- differential cooperation;
- persistent social consequences;
- predictive relationship between history and future treatment;
- disappearance of the effect when memory is ablated.

A universal ground-truth reputation variable should not be introduced if reputation itself is the target phenomenon.

---

# 29. Communities

A future community claim should be based on interaction structure rather than fixed group labels.

Possible evidence may involve:

- persistent network modularity;
- repeated within-cluster interaction;
- reduced cross-cluster interaction;
- stable cluster membership;
- robustness across community-detection methods or thresholds.

Spatial proximity alone should not automatically count as social community.

---

# 30. Hierarchy and power

A future hierarchy claim should distinguish unequal outcomes from social power.

For example, one agent possessing more resources does not necessarily imply hierarchy.

Stronger evidence may involve persistent asymmetric influence such as:

- control over resource access;
- repeated deference;
- centrality in exchange or information;
- ability to alter others' behavior;
- durable asymmetry across interactions.

The model should avoid built-in leader bonuses if emergent hierarchy is the research target.

---

# 31. Settlements

A future settlement claim should distinguish:

```text
temporary crowding
```

from:

```text
persistent spatial organization
```

Possible criteria may include:

- local density exceeding baseline;
- persistence for a predefined interval;
- repeated return to the same location;
- continued occupancy across resource cycles;
- stable functional activity such as exchange or storage.

Environmental hotspots should be controlled for.

---

# 32. Institutions

Institutions are among the strongest claims ECB may eventually make.

They should require more than repeated behavior.

A candidate institution may involve:

- stable rules or conventions affecting multiple agents;
- persistence beyond a single initiating interaction;
- recognizable compliance and violation;
- enforcement or incentive structure;
- transmission or maintenance over time;
- robustness to individual turnover.

If the rule is directly enforced by the simulation kernel, it is a world rule, not an emergent institution.

---

# 33. Norms

A future norm claim should distinguish:

```text
common behavior
```

from:

```text
socially maintained expectation
```

Many agents independently choosing the same action does not necessarily constitute a norm.

Stronger evidence may require:

- expectation of behavior;
- conditional response to violations;
- enforcement, punishment, exclusion, or reputation effects;
- persistence after initial coordination.

---

# 34. Communication conventions

A future symbolic communication system may provide uninterpreted tokens.

If agents independently assign stable shared meanings to those tokens, ECB may study candidate communication conventions.

Evidence should distinguish:

- externally assigned token semantics;
- coincidental token-action correlation;
- learned or negotiated shared meaning.

Useful tests may include:

- token permutation;
- partner replacement;
- communication ablation;
- transfer to new contexts.

---

# 35. Collective intelligence

A future claim of collective intelligence must not be inferred merely from total population performance.

Possible stronger criteria may involve:

- group performance exceeding appropriate independent-agent baselines;
- information integration across agents;
- distributed problem solving;
- robustness to individual failures;
- measurable benefit from interaction structure.

The exact criterion will depend on the task.

Collective intelligence should not become a catch-all label for any successful multi-agent system.

---

# 36. Causal language discipline

ECB documentation should match causal language to the evidence.

Prefer:

```text
is associated with
is consistent with
appears after
is reduced when
is absent under the control
```

until stronger causal evidence exists.

Use stronger language such as:

```text
causes
is necessary for
is sufficient for
```

only when experimental design supports it.

Ablation may support necessity.

Factorial intervention may support interaction effects.

Neither should be implied from correlation alone.

---

# 37. Negative results are results

If a target phenomenon fails to emerge, this should be documented.

Examples:

- trade never becomes persistent;
- communities are unstable;
- communication tokens fail to acquire shared meaning;
- hierarchy disappears across seeds;
- learning policy survives but produces no cooperation.

Negative findings constrain the model and guide future changes.

The benchmark should not evolve solely by hiding unsuccessful experiments.

---

# 38. Failed emergence versus impossible emergence

Failure to observe a phenomenon does not automatically mean the world makes the phenomenon impossible.

The correct diagnosis may be:

```text
mechanism impossible under current rules
```

or:

```text
mechanism possible but current policies fail to discover it
```

or:

```text
metric fails to detect it
```

or:

```text
experiment too short
```

or:

```text
insufficient statistical power
```

These explanations should be distinguished.

---

# 39. Mechanistic interpretation

ECB should aim not only to detect phenomena but to understand how they arise.

A useful scientific progression is:

```text
pattern
→ measurement
→ replication
→ intervention
→ mechanism
```

Mechanistic analysis may involve:

- policy inspection;
- event tracing;
- interaction-network analysis;
- resource-flow analysis;
- controlled perturbation;
- ablation;
- replay.

The benchmark becomes scientifically stronger when a macro-pattern can be connected to lower-level causal processes.

---

# 40. Replay and emergence analysis

Deterministic replay can help diagnose candidate phenomena.

If the same recorded actions reproduce the same physical world-state trajectory, analysts can separate:

- physical consequences of actions;
- policy deliberation;
- later causal interpretation.

Replay does not by itself prove emergence.

It is an observability and verification tool.

---

# 41. Provenance requirement

Every strong emergence claim must remain tied to experiment provenance.

At minimum, documentation should identify:

- software/source identity;
- model configuration;
- policies;
- seeds;
- duration;
- relevant experimental treatment;
- analysis version or procedure.

Directory names are not sufficient provenance.

Analysis should validate metadata where possible.

---

# 42. Reproducibility requirement

A reported phenomenon should be reproducible from the recorded experiment design.

This does not require every stochastic run to produce identical outcomes.

It requires that another run of the documented experiment can reproduce the distribution, frequency, or qualitative regime being claimed within stated uncertainty.

Deterministic components should reproduce exactly where exact reproducibility is intended.

---

# 43. Robustness to moderate parameter variation

A phenomenon that appears only at one exact parameter value may still be interesting.

However, strong claims should test whether it survives reasonable nearby parameter changes.

Examples include:

- population size;
- resource regeneration;
- observation radius;
- productivity heterogeneity;
- communication cost;
- memory horizon.

Robustness does not mean invariance to all parameter changes.

A causal mechanism may legitimately require specific conditions.

The goal is to understand the regime in which the phenomenon exists.

---

# 44. Phase transitions and regime boundaries

Some future ECB phenomena may appear only after a threshold.

Examples might include:

```text
low communication capacity → no coordination
higher capacity → stable convention
```

or:

```text
low scarcity → weak trade
moderate scarcity → exchange network
extreme scarcity → collapse
```

Such regime changes can themselves be scientifically interesting.

They should be mapped systematically rather than described from one visually striking run.

---

# 45. Comparative policy families

A phenomenon observed with one policy family may be policy-specific.

Future experiments should distinguish:

```text
environmental property
policy-specific behavior
general multi-agent phenomenon
```

Where feasible, candidate phenomena should eventually be tested across more than one policy family, for example:

- scripted;
- planning;
- RL;
- LLM.

Generalization across policy families supports stronger claims.

It is not required for every early experiment.

---

# 46. Agent heterogeneity

Heterogeneity may be imposed or endogenous.

ECB must state which.

Examples of imposed heterogeneity:

- different productivity;
- different initial inventory;
- different observation radius;
- different policy class.

Examples of endogenous heterogeneity:

- different learned strategies;
- accumulated wealth;
- social centrality;
- specialization history.

An emergent-inequality claim must not conflate initial inequality with later generated inequality.

---

# 47. History dependence

Many social phenomena may be path-dependent.

Different seeds may generate different stable structures even under the same rules.

This is not automatically a reproducibility failure.

ECB should report:

- whether multiple macrostates exist;
- how frequently each occurs;
- whether early events predict later structure;
- whether perturbations shift the system between regimes.

The relevant reproducible object may be a distribution over outcomes rather than one exact outcome.

---

# 48. Scale dependence

A phenomenon may depend on population size or world size.

For example, a network structure seen with 256 agents may not persist with 32 or 4,096 agents.

Future strong claims should therefore distinguish:

```text
observed at one scale
```

from:

```text
scale-robust
```

Scaling studies should be performed only after the phenomenon has a stable operational definition.

---

# 49. Time-horizon dependence

Some structures may require long horizons to develop.

Others may be transient.

Experiments should therefore report:

- warm-up/transient period;
- observation window;
- total duration;
- whether the phenomenon appears, persists, decays, or transforms.

A structure present only during initialization should not be described as a mature social regime.

---

# 50. Recommended emergence evidence package

A strong ECB emergence result should ideally include:

1. explicit operational definition;
2. documented experiment provenance;
3. multiple seeds;
4. appropriate null/control;
5. persistence measurement;
6. effect magnitude;
7. targeted ablation;
8. symmetry-breaking test where relevant;
9. alternative explanations;
10. negative/failure cases;
11. visual examples for interpretation;
12. reproducible quantitative analysis.

Not every early exploratory experiment needs all twelve.

The strength of the claim should match the strength of the evidence.

---

# 51. Minimal standard for using the word "emergent"

ECB should avoid calling a phenomenon emergent in formal documentation unless, at minimum:

1. the target macrostructure was not directly encoded;
2. an operational metric identifies the structure;
3. the structure persists beyond a trivial transient;
4. it is observed across more than one seed or replication;
5. an appropriate null or comparison condition makes a trivial explanation less plausible;
6. the claim is phrased with uncertainty appropriate to the evidence.

If these conditions are not met, preferred language includes:

```text
observed pattern
candidate phenomenon
exploratory behavior
recurrent structure
synchronization pattern
```

rather than:

```text
emergent institution
emergent civilization
emergent intelligence
```

---

# 52. Strong standard for robust emergence

For a robust emergence claim, ECB should additionally seek:

1. targeted causal ablation;
2. robustness to moderate parameter variation;
3. explicit consideration of environmental and policy artifacts;
4. evidence that inter-agent interaction contributes materially when the claim is social;
5. replication on fresh seeds or held-out configurations;
6. mechanistic interpretation connecting micro-rules to macrostructure.

This is the preferred standard for headline benchmark results.

---

# 53. M0.2 as a methodological negative control

The M0.2 Oracle period-2 cycle provides a useful example of why these standards matter.

Observed facts:

- a highly regular aggregate pattern exists;
- the pattern repeats exactly;
- it is consistent across three seeds;
- it persists for almost the entire run.

Those facts alone might superficially appear to support "emergent synchronization."

However:

- agents do not communicate;
- agents do not coordinate intentionally;
- policies are identical and deterministic;
- the world is highly symmetric;
- food-first tie-breaking introduces a deterministic asymmetry;
- the pattern is readily explained by imposed mechanics and policy structure.

Therefore ECB classifies it as:

> **a reproducible synchronization pattern consistent with imposed symmetry, not emergent social coordination.**

This is the type of distinction this document exists to preserve.

---

# 54. Role of M1 Visual Mode

M1 will make patterns easier to see.

That increases both scientific opportunity and scientific risk.

The visual interface may reveal:

- clustering;
- waves;
- synchronized movement;
- local crowding;
- spatial persistence;
- resource cycles.

Each such observation should initially be treated as:

```text
hypothesis-generating evidence
```

rather than:

```text
confirmed emergence
```

The correct next step is to define a metric and design an experiment.

---

# 55. Future emergence registry

As ECB grows, candidate phenomena should eventually be tracked in a structured registry or experiment documentation.

A future table may contain fields such as:

| Phenomenon | Operational metric | Null | Ablation | Status |
|---|---|---|---|---|
| Division of labor | TBD | TBD | TBD | Not implemented |
| Market coordination | TBD | TBD | TBD | Not implemented |
| Reputation | TBD | TBD | TBD | Not implemented |
| Communities | TBD | TBD | TBD | Not implemented |
| Hierarchy | TBD | TBD | TBD | Not implemented |
| Settlements | TBD | TBD | TBD | Not implemented |
| Norms | TBD | TBD | TBD | Not implemented |
| Institutions | TBD | TBD | TBD | Not implemented |

This document defines the methodological standard.

Specific experiment files should define the actual metrics and thresholds.

---

# 56. Scientific language guide

Preferred wording:

```text
"The data show..."
"The pattern is consistent with..."
"We observe..."
"The phenomenon persists..."
"The control reduces..."
"The ablation eliminates..."
"This supports the hypothesis that..."
```

Use cautiously:

```text
"emerges"
"self-organizes"
"collectively learns"
"forms an institution"
"develops a norm"
```

Avoid without direct evidence:

```text
"the agents decided as a society"
"the civilization wanted"
"the market understood"
"the group intentionally coordinated"
```

Anthropomorphic language may be useful informally, but formal scientific interpretation should remain tied to measurable mechanisms.

---

# 57. Relationship to MODEL_SPEC.md

`MODEL_SPEC.md` defines the scientific world and its allowed dynamics.

This document does not define new mechanics.

Instead, it defines how evidence generated by those mechanics should be interpreted.

A model change belongs in `MODEL_SPEC.md`.

An emergence criterion belongs here or in a specific experiment specification.

---

# 58. Relationship to ARCHITECTURE.md

`ARCHITECTURE.md` protects the boundary between scientific state and infrastructure.

`EMERGENCE_CRITERIA.md` protects the boundary between implemented causes and interpreted phenomena.

Together they enforce two complementary rules:

> **Observers must not become hidden causes.**

and:

> **Causes must not be renamed as emergent outcomes.**

---

# 59. Relationship to METRICS.md

`METRICS.md` should eventually define reusable quantitative measurements.

This document defines what those measurements must accomplish before supporting emergence claims.

Not every metric measures emergence.

Many metrics exist only for:

- debugging;
- viability;
- performance;
- resource accounting;
- reproducibility.

A metric becomes evidence for emergence only within an explicit experimental argument.

---

# 60. Relationship to EXPERIMENTS.md

`EXPERIMENTS.md` should eventually describe the benchmark's experiment families and protocols.

Each experiment that tests emergence should identify:

- target phenomenon;
- treatment;
- controls;
- metrics;
- seed strategy;
- stopping rules;
- analysis;
- claim level.

This document provides the common methodological standard across those experiments.

---

# 61. Decision rule for future reviews

When reviewing a pull request that introduces a new "emergent" phenomenon, reviewers should ask:

1. Is the claimed structure directly encoded anywhere?
2. Is it merely a policy rule?
3. Could environment geometry trivially explain it?
4. Is the metric defined independently of the desired conclusion?
5. Is persistence measured?
6. Are multiple seeds used?
7. Is there an appropriate null?
8. Is there an ablation?
9. Are alternative explanations discussed?
10. Does the language match the evidence?

If several answers are missing, the implementation may still be useful.

The claim should simply be weakened until the evidence catches up.

---

# 62. Methodological north star

ECB is not valuable because it can generate complicated animations.

It is valuable if it can support defensible statements about how macrostructure arises from explicit micro-rules.

The methodological north star is therefore:

> **Do not ask whether a pattern looks emergent. Ask what was encoded, what was measured, what alternatives were tested, what intervention changes it, and whether the result survives replication.**

And the final rule is:

> **Interesting first. Emergent only after evidence.**
