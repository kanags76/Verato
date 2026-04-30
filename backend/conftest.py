import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests that make real Gemini/Vertex AI API calls",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-slow"):
        skip = pytest.mark.skip(reason="Skipped by default — pass --run-slow to run LLM integration tests")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip)
