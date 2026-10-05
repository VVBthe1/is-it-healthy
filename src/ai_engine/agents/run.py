import argparse
import json

from .graph import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyse an ingredient list.")
    parser.add_argument("text", help='e.g. "Sugar, Salt, Preservative (INS 211)"')
    args = parser.parse_args()
    print(json.dumps(run(args.text), indent=2, default=str))


if __name__ == "__main__":
    main()
