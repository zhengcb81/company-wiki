# FF R2 final caller closure

Same3file freeze supersedes ff-repair.json; ff-independent-r1 remains its4P plus open32MiB gap. The ET subprocess now receives a conservative encoded-output allocation derived from its actual raw/source quota, matching ET supervisor encoding reasoning; it no longer falls back to a separate generic32MiB top cap. Other FF callers retain their defaults and actual time/process/usage protections.

New wire test first failed on missing output allocation. Two intermediate4P1F runs had an incomplete new not_found fixture (first schema, then provider/period/count), retained in logs; the complete fixture then targeted5P/0.29s. Ruff2delta files pass. Earlier85P3skip is not rerun or counted twice. No large provider payload is synthesized: the spy proves exact pipe budget propagation, not a real128MiB download. ROOT is separately verifying actual FF→ET public CLI/worker with a small fake HTTP source. No originals/config/key/paid use, own test folders restored absent.
