from argparse import ArgumentParser, Namespace
from collections.abc import Sequence
from typing import Any

import uvicorn


def parse_args(argv: Sequence[str] | None = None) -> Namespace:
    parser = ArgumentParser(description="Knowledge Agent backend server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    return parser.parse_args(argv)


def create_app() -> Any:
    from knowledge_agent.main import app

    return app


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    uvicorn.run(
        create_app(),
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
