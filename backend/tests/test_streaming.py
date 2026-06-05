from knowledge_agent.streaming import sse_event


def test_sse_event_encodes_json_payload():
    assert sse_event("context", {"chunk_count": 2}) == (
        'event: context\n'
        'data: {"chunk_count":2}\n\n'
    )
