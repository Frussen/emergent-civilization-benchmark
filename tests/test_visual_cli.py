from ecb.visual.cli import build_parser
from ecb.visual.server import DEFAULT_HOST, DEFAULT_PORT


def test_visual_cli_defaults_to_oracle_seed_zero_and_loopback() -> None:
    arguments = build_parser().parse_args([])

    assert arguments.policy == "oracle"
    assert arguments.seed == 0
    assert arguments.host == DEFAULT_HOST
    assert arguments.port == DEFAULT_PORT


def test_visual_cli_accepts_random_demo() -> None:
    arguments = build_parser().parse_args(["--policy", "random", "--seed", "7"])

    assert arguments.policy == "random"
    assert arguments.seed == 7
