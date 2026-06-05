import json


def sse_event(name: str, payload: dict[str, object]) -> str:
    data = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"event: {name}\ndata: {data}\n\n"
