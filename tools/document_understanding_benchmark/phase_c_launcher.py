"""Configured production CLI, with the test observer explicitly checked."""


def run():
    from tools.document_understanding_benchmark.phase_c_observer import install

    install()
    from narrative_batch_configured import main

    return main()


if __name__ == "__main__":
    raise SystemExit(run())
