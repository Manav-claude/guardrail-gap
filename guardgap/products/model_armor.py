"""Google Vertex AI Model Armor — sanitizeUserPrompt / sanitizeModelResponse.
Template `guardgap-la` runs every filter at the most-sensitive threshold
(LOW_AND_ABOVE), and the response returns per-filter matchState + confidenceLevel
(RAI: dangerous/harassment/hate_speech/sexually_explicit; plus pi_and_jailbreak,
malicious_uris, csam). One template therefore captures the full gradient — we
reconstruct MEDIUM/HIGH thresholds post-hoc, no extra templates needed.

Model Armor is inherently detect-mode: sanitize APIs return findings; nothing is
blocked. We persist the FULL response in Score.raw so any per-detector /
per-confidence table is recomputable without re-paying.
"""
from __future__ import annotations
import os, time
from ..schema import Score

VERSION = "modelarmor-guardgap-la"
_CLIENT = None
_CONF = {"LOW_AND_ABOVE": 0.33, "MEDIUM_AND_ABOVE": 0.66, "HIGH": 1.0}


def _client():
    global _CLIENT
    if _CLIENT is None:
        from google.cloud import modelarmor_v1
        loc = os.environ["GCP_LOCATION"]
        _CLIENT = modelarmor_v1.ModelArmorClient(
            client_options={"api_endpoint": f"modelarmor.{loc}.rep.googleapis.com"})
    return _CLIENT


def _name() -> str:
    return (f"projects/{os.environ['GCP_PROJECT_ID']}/locations/{os.environ['GCP_LOCATION']}"
            f"/templates/{os.environ['MODEL_ARMOR_TEMPLATE_ID']}")


def score(unit: str, source: str = "INPUT") -> Score:
    from google.cloud import modelarmor_v1 as ma
    from google.protobuf.json_format import MessageToDict
    t0 = time.perf_counter()
    if source == "OUTPUT":
        resp = _client().sanitize_model_response(request=ma.SanitizeModelResponseRequest(
            name=_name(), model_response_data=ma.DataItem(text=unit)))
    else:
        resp = _client().sanitize_user_prompt(request=ma.SanitizeUserPromptRequest(
            name=_name(), user_prompt_data=ma.DataItem(text=unit)))
    dt = (time.perf_counter() - t0) * 1000
    d = MessageToDict(resp._pb).get("sanitizationResult", {})
    blocked = d.get("filterMatchState") == "MATCH_FOUND"
    r, cats = 0.0, []
    fr = d.get("filterResults", {})
    # RAI subtypes
    rai = fr.get("rai", {}).get("raiFilterResult", {}).get("raiFilterTypeResults", {})
    for sub, res in rai.items():
        if res.get("matchState") == "MATCH_FOUND":
            cats.append(f"rai:{sub}")
            r = max(r, _CONF.get(res.get("confidenceLevel", "LOW_AND_ABOVE"), 0.33))
    # pi/jailbreak
    pij = fr.get("pi_and_jailbreak", {}).get("piAndJailbreakFilterResult", {})
    if pij.get("matchState") == "MATCH_FOUND":
        cats.append("pi_and_jailbreak")
        r = max(r, _CONF.get(pij.get("confidenceLevel", "LOW_AND_ABOVE"), 0.33))
    # binary filters
    for key, sub in (("malicious_uris", "maliciousUriFilterResult"),
                     ("csam", "csamFilterFilterResult")):
        if fr.get(key, {}).get(sub, {}).get("matchState") == "MATCH_FOUND":
            cats.append(key)
            r = max(r, 1.0)
    return Score(blocked=blocked, r=r, categories=cats, latency_ms=dt,
                 cost_units=1.0, coverage=1.0, raw=d)
