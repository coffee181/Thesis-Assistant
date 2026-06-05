from knowledge_agent.server import parse_args


def test_parse_args_defaults_to_localhost_port():
    args = parse_args([])

    assert args.host == "127.0.0.1"
    assert args.port == 8765


def test_parse_args_accepts_host_and_port():
    args = parse_args(["--host", "127.0.0.2", "--port", "9000"])

    assert args.host == "127.0.0.2"
    assert args.port == 9000
