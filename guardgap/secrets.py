"""Load and validate credentials from .env. Single source of truth for
what each provider needs, so check_creds.py and the harness agree.
"""
from __future__ import annotations
import os, pathlib
from dataclasses import dataclass
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def get(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name, default)
    return v.strip() if isinstance(v, str) and v.strip() else default


@dataclass
class Provider:
    name: str
    required: list[str]                       # env vars that must be present
    note: str = ""

    def missing(self) -> list[str]:
        return [k for k in self.required if not get(k)]

    def ready(self) -> bool:
        return not self.missing()


# `required` lists what must be in .env for that provider to be usable.
PROVIDERS: list[Provider] = [
    # commercial services evaluated in the paper
    Provider("bedrock",
             ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION",
              "BEDROCK_GUARDRAIL_ID", "BEDROCK_GUARDRAIL_VERSION"],
             "run infra/aws_provision_guardrail.py to fill the guardrail id/version"),
    Provider("azure_prompt_shields",
             ["AZURE_CONTENT_SAFETY_ENDPOINT", "AZURE_CONTENT_SAFETY_KEY"],
             "run infra/azure_provision.sh or create a Content Safety resource"),
    Provider("azure_text",
             ["AZURE_CONTENT_SAFETY_ENDPOINT", "AZURE_CONTENT_SAFETY_KEY"],
             "same Content Safety resource as Prompt Shields (text:analyze endpoint)"),
    Provider("model_armor",
             ["GCP_PROJECT_ID", "GCP_LOCATION", "MODEL_ARMOR_TEMPLATE_ID"],
             "run infra/gcp_provision.sh; auth via gcloud ADC"),
    # open reference tier (run in the models env)
    Provider("prompt_guard2",
             ["HF_TOKEN"],
             "gated: accept the licence on the model page; run in the models env"),
    Provider("protectai_deberta", [],
             "free/local, ungated; run in the models env"),
    Provider("qwen3guard", [],
             "free/local, ungated; run in the models env"),
    # experimental adapter, not evaluated in the paper
    Provider("llama_guard4",
             ["LLAMA_GUARD_API_KEY", "LLAMA_GUARD_MODEL", "LLAMA_GUARD_PROVIDER"],
             "hosted via openrouter/together/groq; not used in the paper"),
]


def status() -> dict[str, bool]:
    return {p.name: p.ready() for p in PROVIDERS}
