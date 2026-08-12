# Emergent Civilization Benchmark — Agent Instructions

ECB is an open-source scientific multi-agent simulation and benchmark for
studying emergent social dynamics and long-horizon autonomous agency.

## Core principles

1. Never encode a claimed emergent phenomenon directly unless MODEL_SPEC.md
   explicitly defines it as an imposed world rule.

2. Always distinguish:
   - imposed mechanisms,
   - agent policies,
   - derived analytical metrics,
   - emergent phenomena.

3. The simulation engine must be completely independent from visualization.

4. A run with the same configuration, seed, and agent actions must be
   deterministic and reproducible.

5. All randomness must flow through project-controlled seeded RNG instances.
   Do not use hidden or unseeded randomness.

6. Agent policies must never mutate WorldState directly.
   Policies receive Observation objects and return Action objects.

7. Policies may access only information included in their Observation.
   Hidden simulation state must never leak into agent policies.

8. Prefer minimal falsifiable mechanisms over realistic but unnecessary
   complexity.

9. Do not silently modify scientific rules.
   Changes to world mechanics require corresponding changes to MODEL_SPEC.md.

10. Every world rule must have automated tests for relevant invariants.

11. Headless execution is the canonical simulation mode.
    Visual Mode consumes simulation state/events but must not affect outcomes.

12. Design interfaces so scripted, planning, RL, and future LLM policies can
    inhabit exactly the same world and use the same action/observation API.

13. Experiments must record at minimum:
    - configuration,
    - seed,
    - software version,
    - metrics,
    - relevant events.

14. Never interpret a phenomenon as emergent merely because it looks
    interesting in a single run. Emergence claims require quantitative metrics,
    multiple seeds, controls, and ablations.

## Engineering priorities

Correctness > reproducibility > interpretability > performance > features.

Do not optimize prematurely.

Target development hardware includes a MacBook Air M1 with 8 GB RAM.

The project must support both:
- interactive Visual Mode,
- high-speed headless batch experiments.

## Current project status

The project is in MVP v0.1 design/bootstrap.

Do not implement new economic, political, institutional, social, or cognitive
mechanisms unless they are explicitly specified in MODEL_SPEC.md.

When scientific requirements are ambiguous, preserve the simpler mechanism
rather than inventing additional rules.