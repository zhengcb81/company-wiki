# R7 final core — independent NEEDS_FIXES

Reviewed all16 final files (11source/5tests), manifest66d79a50. Frozen-source identity and all new evidence are in sibling JSON. No source/Git/PWF edit.

## P2: final metadata work can ignore cancellation/deadline

`source_availability.py` checks the injected budget on each next discovery/read, but after the last actual metadata read there is no next iteration or final check. With one exact location, cancelling the actual same LocalReadBudget or expiring its deadline immediately after that read still returns availability proof. New2controls both fail with DID NOT RAISE.

The author's test used cap2 and was caught by the second observe_entry; it did not protect the final/only location. This is the same resource-stop cause, not a request for another permission. Audit stored-only inline parse too. Minimal repair belongs to this owner: check the same parent after actual metadata/parse work and before returning proof. Preserve independently known evidence across genuine byte/discovery exhaustion, but do not swallow explicit cancellation or hard deadline; no budget replacement/reset, fixed-size fallback or global refusal.

## New independent evidence

12new tests:10P2F/2.61s. Positive cases cover137explicitmembers and actual >2MiB object read/write with SHA; final/scratch stop before creation; public canonical import preserving full large provenance with wrong-original SHA control; typed source prose versus sibling metadata/unknown-envelope paths; cycle/nonfinite JSON;67distinctlocations with only the final large capture valid; shared consumed parentbytes across repeated calls. The5author test deltas were read and the three parent caller forwarding sites inspected.

No author144/34/9groups were repeated, no H1/real original/model/fee/download, no ownINV self-review. Full reproducer/log/JUnit are embedded. ROOT should fix this unique boundary and provide final SHA for a small independent delta recheck; current version is not signed PASS.

Owned temporary directory is initially absent and will be restored after exact containment/nonreparse checks; all required evidence is preserved first.

Final cleanup: exact parent/nonreparse checked before deleting only ownedroot; 82files / 4543460.0bytes removed, target restored absent. Reproducer preserved in JSON.
