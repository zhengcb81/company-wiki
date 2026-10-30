# D00 canonical calendar input repair

Base: 97d55a2dccb12ffd3eb114b8c08fccba09418826.
An independent actual SW proof CLI → CWP canonical CLI query found that 2026-02-30T00:00:00Z reached the proof process and became an unavailable envelope instead of blocked invalid_as_of.
The local boundary now retains the strict UTC syntax check and also parses the calendar with Python datetime before any owner call. Impossible dates/times are rejected with the existing CanonicalBrowseError("invalid_as_of"). Public schema and owner engines are unchanged.

Author verification:
- Before fix: six invalid calendar cases RED, three valid UTC/leap-day/fraction controls PASS.
- After fix: nine boundary cases PASS; inputs use a sentinel at the owner boundary to prove invalid requests make no owner call.
- Independent reviewer accept_previous_proof_cwp will replay the actual CLI RED and affected controls at the committed candidate; final acceptance remains in D00 report.
- Initial pytest base path was automatically relocated by the owner's existing Windows hook and removed successfully; no production or original files used. No model/download/network.
Only the canonical facade, a new private calendar test, and this note change. Not merged to owner main or the external author's branch.
