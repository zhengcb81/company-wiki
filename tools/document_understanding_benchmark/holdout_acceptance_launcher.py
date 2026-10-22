"""Test-side launcher around the unchanged configured production CLI."""
from tools.document_understanding_benchmark.holdout_acceptance_observer import install


def main():
    install()
    from scripts.narrative_batch_configured import main as configured_main
    return configured_main()


if __name__ == '__main__':
    raise SystemExit(main())
