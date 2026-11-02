# FF R2 independent delta review — scoped PASS

Author ff-repair-r2.json SHA `30a80f3d301b68b0371b35482cb6376709fb6cffaff4bdf42ba7084093f2e594`; all3 actual file SHA saved before/after and unchanged. Initial ff-independent-r1.md/json remains intact; its ET pipe-allocation gap is closed by this delta, together with its four earlier explicit-budget/parent-deadline/usage controls.

Independent **4P /0.56s**:17bytes,21,000,001bytes and128MiB budgets propagate unchanged to ET raw/body, while pipe allocation derives from the actual budget and may exceed generic32MiB. No large provider payload allocated. Provider120s/outer123s and complete measured2requests/3bytes remain exact. The existing transport really stops an owned child while reading1026UTF8bytes through an explicit1024byte cap, before the child can complete its20s sleep; owned PID is dead.

The actual ET call now forwards stdout_cap_bytes=18*actual max_bytes+2MiB to the existing while-read budget owner, with JSON/base64 expansion accounted for. It does not substitute a higher constant limit. Credential/import/unknown-usage/no-retry/process lifetime code is unchanged. No85/whole-suite rerun.

This is scoped engineering PASS, not all-FF or real-company download acceptance. ROOT owns separate actual public FF->ET CLI->worker offline integration. Other callers retain defaults as requested: _verified_open still does not derive stdout from known SourceRef.byte_size; a>32MiB original is a static residual candidate, not publicly executed here. ROOT was notified; this delta is not a claim that all possible FF representation gates are gone.

Full3SHA, exact probe/log/JUnit, closure relationship and cleanup: [ff-independent.json](ff-independent.json). Self-owned initially absent tmp/fi72 restored absent, no FF source/config/key/Git writes and no network/paid activity.
