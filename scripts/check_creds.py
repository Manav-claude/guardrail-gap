#!/usr/bin/env python
"""Preflight: for every provider with credentials in .env, hit its cheapest
real endpoint and report OK / FAIL. Run this before any experiment run.

    python scripts/check_creds.py

Providers with blank credentials are reported as SKIP, not FAIL.
"""
from __future__ import annotations
import sys, pathlib, traceback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from guardgap import secrets as S  # noqa: E402

BENIGN = "hello, how are you today?"


def check_bedrock() -> str:
    import boto3
    rt = boto3.client("bedrock-runtime", region_name=S.get("AWS_REGION"))
    r = rt.apply_guardrail(
        guardrailIdentifier=S.get("BEDROCK_GUARDRAIL_ID"),
        guardrailVersion=S.get("BEDROCK_GUARDRAIL_VERSION"),
        source="INPUT", outputScope="FULL",
        content=[{"text": {"text": BENIGN}}])
    return f"action={r.get('action')} (units={r.get('usage', {}).get('contentPolicyUnits')})"


def check_azure_prompt_shields() -> str:
    import httpx
    ep = S.get("AZURE_CONTENT_SAFETY_ENDPOINT").rstrip("/")
    url = f"{ep}/contentsafety/text:shieldPrompt?api-version=2024-09-01"
    r = httpx.post(url, headers={"Ocp-Apim-Subscription-Key": S.get("AZURE_CONTENT_SAFETY_KEY")},
                   json={"userPrompt": BENIGN, "documents": []}, timeout=30)
    r.raise_for_status()
    return f"attackDetected={r.json()['userPromptAnalysis']['attackDetected']}"


def check_azure_text() -> str:
    import httpx
    ep = S.get("AZURE_CONTENT_SAFETY_ENDPOINT").rstrip("/")
    url = f"{ep}/contentsafety/text:analyze?api-version=2024-09-01"
    r = httpx.post(url, headers={"Ocp-Apim-Subscription-Key": S.get("AZURE_CONTENT_SAFETY_KEY")},
                   json={"text": BENIGN, "outputType": "EightSeverityLevels"}, timeout=30)
    r.raise_for_status()
    sev = max((c.get("severity", 0) for c in r.json().get("categoriesAnalysis", [])), default=0)
    return f"max severity={sev} (0-7 scale)"


def check_model_armor() -> str:
    from google.cloud import modelarmor_v1
    loc = S.get("GCP_LOCATION")
    client = modelarmor_v1.ModelArmorClient(
        client_options={"api_endpoint": f"modelarmor.{loc}.rep.googleapis.com"})
    name = (f"projects/{S.get('GCP_PROJECT_ID')}/locations/{loc}"
            f"/templates/{S.get('MODEL_ARMOR_TEMPLATE_ID')}")
    resp = client.sanitize_user_prompt(request={
        "name": name,
        "user_prompt_data": {"text": BENIGN}})
    return f"result={resp.sanitization_result.filter_match_state}"


def check_prompt_guard2() -> str:
    from guardgap.products import prompt_guard2
    return f"r={prompt_guard2.score(BENIGN).r:.3f}"


def check_llama_guard4() -> str:
    import httpx
    prov = S.get("LLAMA_GUARD_PROVIDER", "openrouter")
    base = {"openrouter": "https://openrouter.ai/api/v1",
            "together": "https://api.together.xyz/v1",
            "groq": "https://api.groq.com/openai/v1"}[prov]
    r = httpx.post(f"{base}/chat/completions",
                   headers={"Authorization": f"Bearer {S.get('LLAMA_GUARD_API_KEY')}"},
                   json={"model": S.get("LLAMA_GUARD_MODEL"),
                         "messages": [{"role": "user", "content": BENIGN}],
                         "max_tokens": 16},
                   timeout=60)
    r.raise_for_status()
    return f"reply={r.json()['choices'][0]['message']['content'][:20]!r}"


def check_protectai_deberta() -> str:
    from guardgap.products import protectai_deberta
    return f"r={protectai_deberta.score(BENIGN).r:.3f} (free/local)"


def check_qwen3guard() -> str:
    from guardgap.products import qwen3guard
    return f"r={qwen3guard.score(BENIGN).r:.2f} (free/local)"


CHECKS = {
    "bedrock": check_bedrock,
    "azure_prompt_shields": check_azure_prompt_shields,
    "azure_text": check_azure_text,
    "model_armor": check_model_armor,
    "prompt_guard2": check_prompt_guard2,
    "llama_guard4": check_llama_guard4,
    "protectai_deberta": check_protectai_deberta,
    "qwen3guard": check_qwen3guard,
}


def main() -> None:
    by_name = {p.name: p for p in S.PROVIDERS}
    any_fail = False
    for name, fn in CHECKS.items():
        prov = by_name[name]
        if not prov.ready():
            print(f"SKIP  {name:22} missing {prov.missing()}  ({prov.note})")
            continue
        try:
            print(f"OK    {name:22} {fn()}")
        except ModuleNotFoundError as e:
            # e.g. torch absent in the core venv -> not a failure, wrong venv
            print(f"SKIP  {name:22} needs models venv ({e.name})")
        except Exception as e:  # noqa: BLE001
            any_fail = True
            print(f"FAIL  {name:22} {type(e).__name__}: {str(e)[:160]}")
            if "-v" in sys.argv:
                traceback.print_exc()
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
