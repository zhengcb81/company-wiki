# Paid-response durability implementation handoff (awaiting independent review)

Eight owned files and exact SHA values are in implementation-handoff.json. No commit/push, no PDF/real API/key/config/original access. Default legacy caller behavior remains disabled for this new byte port; ROOT enables it only for the new source-extractive protocol.

## Construction and ownership

`PaidResponseArtifacts(objects, max_response_bytes=<actual HTTP cap>, preflight=callback)` wraps existing LocalNarrativeObjectStore or ROOT's existing budgeted object port. Inject `paid_responses=artifacts` into BudgetedNarrativeCaller. Before a NEW reserve/POST, caller validates actual model/adapter/prompt/request identities can make a bounded pin, then invokes callback(max_response_bytes). ROOT callback must account for persistent max body + temporary writer/WAL overhead under existing caps; the port creates no new guard or budget origin. Replay never invokes model credentials or preflight/POST.

HTTP.generate optional response_sink receives only complete bounded body/status/duration before envelope decoding. The existing body cap stays262144; final content128KiB and final artifact/output limits remain separate. Complete empty/malformed bodies are also durable and replay their original error, not a repaired reply. Pin body SHA and ledger final-content SHA have distinct meanings.

AUTO schema7 adds ONLY nullable paid_response_json to the existing reservations table; v5/v6 read-existing preparation and additive migration are supported. A typed strict canonical pin references ONE content-addressed body; no body in attempt/result_json, no new table/task/cache/ledger and no raw visible bundle.

RunStore.attach_paid_response verifies original attempt token/generation/request/model/prompt; late original evidence is permitted but gives no current publication right. Caller recovery checks same run/job frozen input/handler, exact task/input+HTTPbody request hash, actual model/adapter/prompt and actual body hash/size; missing/unbound/clipped/changed bytes remain unavailable with0 automatic resend. Existing usage settles against ORIGINAL paid attempt, including unknown->known when exact response proves usage; no new provider reservation is made.

## ROOT resume assembly

After enabling the same owned runtime generation, use AutomationStore.retry_paid_narrative_summary(run_id,job_id,request_sha256,now,expected_generation) for exact new-protocol paid unsuccessful jobs. It retains original attempts, results, charges, unknown history; restores summary READY and only same-event/run unattempted verify jobs marked DEPENDENCY_TERMINAL. ROOT must bypass the batch's current terminalfailed early return only for this path. It is not a general job reset or permission flow.

Caller actually verifies saved bytes before reopening original output0. RunStore.reopen_paid_output checks current active lease, same frozen membership/request/body pin, no effects/succeeded attempts/positive output, and original output0; it re-reserves that same slot. Repeated explicit reopen refuses. Existing finalizer can later settle that original reservation to final bytes. No successful output can be overwritten, old failure results remain readable, and no fee moves to the replay lease.

## Verification and honest boundaries

Behaviour RED18FAIL/2PASS; preflight/empty4FAIL/1PASS; frozen membership2FAIL. Concentrated old/new caller/HTTP/runstore/schema tests168PASS/20.98s. Final focused28PASS/9.06s after the narrow membership fix. New loopback integrates actual HTTP -> durable body -> simulated decoder process death -> coordinator marks unknown -> new AUTO lease -> credentials absent/POST forbidden -> same92tokens original reservation, only1POST and1byte object. Final publication/sourcecard truth remains ROOT's larger integration node.

Ruff passed. Independent review is still required before handoff is accepted. Tiny retry positive-output precheck added after final28 test and explicitly requires independent delta control. Raw response capture cannot recover a remote charge that happened before local durable bytes; keep that uncertainty and forbid blind resend. Object-write-before-AUTO-attach crash can leave a small unbound object; do not guess recovery from it. Old failed v4 responses never become new protocol output.

ROOT still owns factory/batch/sourcecards/summarize/verify/compaction and PWF. No compaction code was modified by this lane.

## Final independent reception

ET independent reviewer returned PASS against all eight exact final SHA values, including terminal-failure/new-lease0POST/original-usage-once and positive10byte output deny controls. No confirmed remaining source defect. ROOT may now integrate and separately modify store.compaction. This remains engineering acceptance, not full paid-content C completion.

Owned test Temp cleanup was rejected by the tool platform before execution; no alternate delete channel used. cleanup.json records NOT_CLEAN/platform refusal. Only synthetic DB/response fixtures remain; no original/config/secret files were copied. Independent reviewer likewise reports its own small fixture cleanup failure/refusal honestly.
