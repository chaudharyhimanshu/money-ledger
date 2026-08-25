"""
Run the replay and print the report.

    ./.venv/bin/python run.py
"""

from ledger.engine import Engine
from ledger.report import render
from stream import EVENTS


def main() -> None:
    engine = Engine()
    engine.replay(EVENTS)
    print(render(engine, EVENTS))


if __name__ == "__main__":
    main()
