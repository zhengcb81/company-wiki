# ROOT source-layer acceptance — 2026-10-11

191 focused implementation tests and 13+1 independent public-API probes pass.
The actual unchanged 41-case offline chain now passes 40, with the last failure
in ET-to-FF cutoff diagnostics before CWP import. The source fix is accepted
within its scope: verified source facts belong to the writer/source layer,
irrelevant old periods do not obstruct acquisition, same-period reuse verifies
raw SHA, and registration/facts/reactivation recover through one transaction.

12 frozen product files are included, including canonical_scope.py and both
new tests. Original files/configuration are preserved. No new permission,
canary, review receipt, identity database or consumer filesystem interface.
The independent report and original 40/1 evidence remain in the mother W06
root-ff-matrix-acceptance directory. ROOT owns the ET/FF diagnostic repair,
final 41-case replay, shared PWF and publication. The whole PWF remains open.

Source runtime is read by consumers from the configured canonical CWP code
root; there is no separate company-wiki skill copy to overwrite.
