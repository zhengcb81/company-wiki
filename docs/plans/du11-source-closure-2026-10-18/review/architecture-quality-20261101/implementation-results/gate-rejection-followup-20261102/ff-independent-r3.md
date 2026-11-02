# FF R3 final scoped independent review — PASS

Author ff-repair-r3.json SHA `78b3b6f16d4f8788b1f968c460cb54d03e22a78bacd2eddf5855dfa564ba644f`; all4 delivered file SHA independently measured before/after and unchanged. Prior ff-independent-r1.json and ff-independent.json remain historical with their original boundaries. The remaining known-original32MiB/metadata64KiB pipe mismatch is closed at the actual caller.

The caller now derives stdout from exact SourceRef.byte_size and explicitly requests complete stderr metadata. The unique process owner only adds explicit None stderr support; positive channel budgets still stop at cap+one, actual deadline/tree cleanup/nonzero/UTF8 behavior is unchanged. Original SHA/size, SourceRef identity and receipt JSON checks remain enforced.

Independent **6P /2.35s**. A real owned child sends3B original plus90KBChinese metadata; the full30000character title survives. Wrong original SHA, wrong receipt identity and large malformedJSON each reject in one call. Explicit1024B stderr still stops1025B during a live20s child sleep and kills its PID. None stderr allows90KB but still honors an actual1s deadline and reclaims its PID.

No85test/fullUnit rerun, large-original fixture, provider/network/paid/key/config/production activity. The real process boundary carries only self-created tiny fixtures; ROOT separately owns actual public FF->ET CLI/worker integration and normal publication.

Exact4SHA, runnable independent probe, full log/JUnit and own initially absent tmp/fi73 cleanup: [ff-independent-r3.json](ff-independent-r3.json). No author source/test/Git/PWF modification by reviewer. No further scope expansion.
