# W03 grouped M2 independent review

Status: **NOT ACCEPTED pending one malformed-wire fix and responsibility-fixture corrections**. Review used actual pending four-source worktree; no source/test edits by reviewer, no externalHTTP/paid calls and no key/config inspection. All runs use reviewer-owned TemporaryDirectory roots, bytecode/cachedisabled, withnormalOS Git/pytest execution; initial sandbox Gitworktree lookup failed before normalOS diff succeeded and is anenvironment observation, not product RED.

## Actual verification

- New contracts:22PASS0SKIP1.65sec (`test_narrative_output_plan.py`, `test_summary_group_coverage.py`). Benign unknownasyncio_mode warning under disabled plugin autoload.
- Independent six-case in-memory probes: canonical-IDfullgroup accepted; unknowncanonicalgroup rejected; mixedanalyst/company declaredgroup rejected byrole; additional undeclared partialgroup getsneeds_review; explicitnullcomplete wronglyaccepts asdraft/needs_reviewFalse; explicitnullpartial accepts withneeds_reviewTrue.
- Existing concentrated compatibility/role/caller bundle:93collected,81PASS12FAIL1.77sec. Both alias, transport and budgetedcaller suites passed. Elevenpartialclaimrecovery failures and oneuncitedqualityfailure are explained below, not counted asgreen.
- Truncationcap/configoutput/settings are bound toactual HTTPbytes reservation; one provider call withknown2716/8192tokens is settled once, repeatedsamecontextcall denied without anew request. Terminal truncation producesno success artifact and static finish_reason/byte-count diagnostics. Exact tests distinguish heuristic prompttarget from actualconfigured hardbound.

## Finding F1: explicit JSONnull group declaration bypasses malformed-shape validation

Source `narrative_model.py`: `declarations = claim.pop("evidence_group_ids", None)` and `_validate_group_declarations` returningonNone conflatesabsentlegacyfield withpresentnull. Reproducer: validHK group claim withids e1/e2 andliteral `"evidence_group_ids": null` isaccepted asstatusdraft, needs_reviewFalse. The schema promisesarrayonly; design rejects malformeddeclaration rather than silentlystripping it. Partialcontext diagnostics do not resolve thecomplete-null case.

Fix recommendation: distinguish absence withkeypresence/sentinel; absentlegacyfield retainscompatibility andpartialcontextdiagnostic, presentnull raises safeGROUP_DECLARATION. Keepentireinvalidclaim discard; a good sibling survives withsummaryneeds_review. Add RED fornullcomplete andnull+goodsibling; no citationpadding or assertionrelaxation.

## Finding F2: existing recovery/quality test fixture conflates atomic context with independent evidence

`support.narrative_model_request_fixture.selection(2)` givesbothdifferentpage, complete independentbusinesssentences the SAMEselection_group_id. Eleven`test_one_bad_claim_preserves_valid_claim_and_visible_quality` cases citeonlye1 andexpectclaimneeds_reviewFalse; `test_exported_evidence_quality_is_visible_even_when_not_cited_by_retained_claim` doeslikewise. NewW03 partial-atomic-group diagnostic correctly marksneeds_reviewTrue underthatfixture. This is a test responsibilitycollision, not proof of a productregression or permission toremovepartialcontextdiagnostics.

Fix recommendation: useindependent singleton/nogroup sourcefixtures in recovery-only/uncitedquality tests, preserving their originalFalse assertions (bad sibling oruncitedquality must not contaminatea standalonegoodclaim). Keep explicitatomicpartialcaseassertTrue in newcontracts. Donot globallymakegoodclaimflagsTrue just togreen thesuite.

## Checked scope and remaining limitations

No automaticcitationpadding observed. Model-only `evidence_group_ids` isremovedbefore exactsix-key public parsing; canonicalID andalias mapping bothwork. Unknown/malformed strings/arrays discardwholeclaims; badsiblingmarks summarypartialdiagnostic. Mechanicalclosure cannotclear originalOCRflags. Explicit[] mayretainnarrow claim withpartialcontextneeds_review; no source readapproval gate.

The newsource-derived fixtures identify syntheticbindings; USsealedthree-membergroup remainsdistinct from correctedW02-styletwo-membergroup+unrelatedbullet. New schema/promptversions and fullcanonical groupidentity affect inputfingerprints, evenwhencompactHTTPaliasmembershipunchanged. Configuration max_tokens/model/temperature/thinking are preserved; outputplan is openlyheuristic. No realprovider generation orcompanyM3 semanticacceptance is claimed by these local tests.

Reviewed four-source SHA256 snapshot:

- src/company_wiki/automation/narrative_model.py: `d8e98bb189e97839cffc8e3aa4a21462284c1bc2592da70ad58244832d535485`
- src/company_wiki/automation/narrative_http_model.py: `b1eb34662e52600a7d97d73c6a60032f7bad5dfe7e1168a32498560f7f534184`
- src/company_wiki/automation/narrative_model_caller.py: `4720c433e70d831474cab96789c68c9180988e3cfc5572cac5454cbcbd765d84`
- src/company_wiki/automation/narrative_summarize.py: `4e69bf5ca4c2ba40060eafb0ae2ee615f89abb57cef634d0aa2b617177d7e54b`

Owned reviewer TEMP roots restored absent: True.
