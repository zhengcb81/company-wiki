# W08 explicit local qualifier dependency: read-only design

Status: diagnosis and recommendation, no production or test edit.

## Existing ownership

- `narrative_continuity._Analysis.edge` proves native source/frame/scope/font/column/ordinal and block geometry. Different blocks stop after a complete source sentence; do not turn all sentence neighbours into one native semantic window.
- `narrative_antecedent.build_antecedent_windows` owns finite source order/scope predecessors; same-page ordinal adjacency alone does not prove a common physical column.
- `OperatingRelationSession.reference_closure` deliberately handles named family references. It detects singular device deictics but does not resolve them; preserve that contract.
- `SourceOperatingSession` already shares source-identity caches, relations, original offsets, reference checks and the caller WorkBudget. This is the right orchestration owner for a local explicit qualifier dependency.
- `within_reference_envelope` already expands source carriers and counts body+heading+reference originals against 8 units, 4 blocks, 2048 chars.

## Observed common root

The public project-body test requires a following source block explicitly qualifying the same delivered equipment. Existing physical continuity intentionally closes at the first complete sentence; existing family-reference closure intentionally ignores singular descriptive devices. Their absence is not proof that the next explicit qualifier is unrelated. Generic future language must not be used as a replacement identity proof.

The neutral probe shows a second independent shared grammar defect: `该设备仍需客户完成认证，预计下一期才能进入量产。` is currently qualification/positive/current with attribution other. This is not a completed customer approval and must be repaired in the sole existing relation grammar before dependency decisions consume its state. `该设备尚未完成量产认证...` is correctly negative/not_yet. Generic future internal-process prose returns no relation and no device deictic. Full refs, observed hashes and exact probe outputs are in diagnosis.json.

## Minimal shared design

1. Reuse the native geometry owner to expose positively measured adjacent-body edges separately from joined-line continuity. Keep terminal punctuation meaningful. Same source, real section/project, role, frame, column, font, source order and measured bbox/block rules remain required. A missing physical proof remains unknown.
2. Fix passive/pending certification in the existing operating-state grammar and field resolver, retaining exact predicate/qualifier refs. Do not add another regex classifier to narrative_reading. Customer is the party performing approval; its actor attribution need not be rewritten as issuer.
3. Add a call-scoped qualifier-dependency operation to SourceOperatingSession using its already cached relations plus find_product_deictic/head_class and original object refs. Accept explicit deictic reference, a unique compatible preceding source object and an actually observed operating restriction state. Named competing objects or mismatched heads remain ambiguous. Never infer completion/revenue from shipment.
4. Reverse only that proved following-qualifier edge into the previous fact required_context. Reuse the existing budget graph/closure; keep qualifier independently source-addressable, not a synthetic product statement. Check the combined original envelope, including actual heading, before expansion. A tight selector cap must withhold the unsupported earlier fact instead of detaching its qualifier.
5. Stop at the next independent issuer fact or proof boundary. Do not recursively ingest all future sentences or make an entire project atomic. Cache by source identity/current owner and charge existing WorkBudget before every scan or edge allocation.

## Validation at one substantial node

Use the two current public-selector explicit-qualifier cases and reverse controls listed in diagnosis.json. Add mismatched device/third-party, competing object, column/frame/ordinal/source boundary and low-resource tests. Confirm native wrap tests unchanged, no source rewrite, no second budget/store, no 96/48000/16M increase. Only then inspect the real annual corpus at the ROOT-owned major content checkpoint.

No raw documents were opened, no paid calls or downloads occurred, and no production/test/Git files were edited. One attempted nonexistent read of structure/references.py failed harmlessly; actual reference owner is operating_states/relations.py.
