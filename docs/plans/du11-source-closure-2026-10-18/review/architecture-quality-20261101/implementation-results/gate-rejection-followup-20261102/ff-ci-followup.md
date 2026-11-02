# FF retired timeout oracle follow-up

Remote f9639caa run41494644371 failed the focused suite; its public annotation exposes exit1 only. ROOT separately ran the affected3transport/lifecycle files once:53P1F/24.95s, failing only the old test expecting explicit90seconds to become60. The timeout-owner contract deliberately no longer clips valid explicit allocations. Rename that test and require actual90seconds plus3seconds cleanup, preserving its child-observation assertions. No runtime change or weakened actual deadline/usage/source controls. Existing new tight-parent/actual timeout and independent raw/receipt controls remain.

The remote exact test identity cannot be inferred from its generic annotation alone; final new exact CI verifies the repository. No local full focused or all-Unit retry. The original remote failure and local isolated failure remain in evidence; after fixing this expectation only its node is rerun.
