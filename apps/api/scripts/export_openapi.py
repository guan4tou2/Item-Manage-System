"""將 OpenAPI JSON 匯出至 stdout，供 api-types 產生型別。"""
import json
import sys

from app.main import create_app


def main() -> int:
    app = create_app()
    try:
        sys.stdout.write(json.dumps(app.openapi(), indent=2, ensure_ascii=False))
    except BrokenPipeError:
        # head 等讀取端提早關閉 pipe 時，仍視為正常結束。
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
