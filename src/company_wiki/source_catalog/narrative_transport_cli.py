"""Compatibility executable for deployed narrative reader commands.

The narrative read command is composed in the automation application layer.
This historical module path supports execution via ``python -m`` only.
"""

if __name__ == "__main__":
    from company_wiki.automation.narrative_transport_cli import main

    raise SystemExit(main())
