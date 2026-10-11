# Micro probe plan (fixed before execution)

1. Explicit free budget 0.00: pure audit builder vs CWP native budget constructor. Expected compatibility: zero cap is legal for free work; this does not run native acquisition.
2. Negative budget -0.01: pure helper and native budget constructor must reject.
3. NaN budget: pure helper and native budget constructor must reject; non-finite zero change must not loosen this.
4. Outer/body discrepancy: P1 / 100 / 1.00 outer vs P2 / 1000 / 10.00 JSON body. Determine acceptance and exact byte SHA; no provider/model child.
5. Local CLI build → W11 capture → supplied fake native child on unchanged discrepant body. Determine builder/frozen/consumed SHA equality and diagnostic boundary. Run only inside this reviewer output, retain provenance. No provider/model call.
6. Fresh local CLI chain after intentionally changing reviewer-owned generated request before capture. Determine whether existing capture receives builder digest, and whether it reports the changed current bytes honestly. This is compositional contract coverage, not an old W11 defect or a native provider enforcement test.

At most six named probes. All source/fixtures/tests remain read-only; Python -B disables bytecode writing. Native CWP module is standard-library-only budget construction, never a provider invocation. No GET/model/provider fees. No suite rerun.