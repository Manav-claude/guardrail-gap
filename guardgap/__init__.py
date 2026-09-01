"""GuardGap — measuring the configuration gap in commercial LLM guardrails.

See ../research/05-paper-build-spec.md for the design. This package is the
experiment harness; the runner/metrics modules land in the next phase.
"""
__version__ = "0.0.1"

# Load .env once so HF_TOKEN and provider creds are available to every module
# (both the core and models venvs), regardless of entry point.
try:
    import pathlib
    from dotenv import load_dotenv
    load_dotenv(pathlib.Path(__file__).resolve().parents[1] / ".env")
except Exception:
    pass
