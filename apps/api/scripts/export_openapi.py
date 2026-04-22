"""Export OpenAPI JSON to stdout for the api-types package."""
import json
import sys

from app.main import create_app


def main() -> int:
    app = create_app()
    sys.stdout.write(json.dumps(app.openapi(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
