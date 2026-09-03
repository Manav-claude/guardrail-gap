"""GuardGap: per-detector measurement of commercial LLM guardrails under
multi-turn attacks. See README.md and RUNNING.md."""
__version__ = "1.0.0"

# Load .env once so HF_TOKEN and provider creds are available to every module
# (both the core and models envs), regardless of entry point.
try:
    import pathlib
    from dotenv import load_dotenv
    load_dotenv(pathlib.Path(__file__).resolve().parents[1] / ".env")
except Exception:
    pass
