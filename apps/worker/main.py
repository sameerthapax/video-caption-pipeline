from __future__ import annotations

from time import sleep

from pipeline.pipeline import run_worker_iteration


def main() -> None:
    while True:
        run_worker_iteration()
        sleep(2)


if __name__ == "__main__":
    main()
