#!/usr/bin/env python
"""Provision the Bedrock guardrail used by the experiment — via boto3, no
AWS CLI or Terraform required.

It creates ONE guardrail with every content filter at HIGH and the
prompt-attack filter at HIGH (input side; the API forbids an output
strength on PROMPT_ATTACK), publishes a numbered version, prints the
identifiers, and writes them to provisioned.aws.json. Paste the two
values it prints into your .env as BEDROCK_GUARDRAIL_ID / _VERSION.

Prereqs: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION in .env,
on an IAM identity allowed to bedrock:CreateGuardrail + CreateGuardrailVersion.

Run:  python infra/aws_provision_guardrail.py
Idempotent: if a guardrail named GUARDRAIL_NAME already exists it is
reused, not duplicated.
"""
from __future__ import annotations
import json, os, sys, pathlib
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

GUARDRAIL_NAME = "guardgap-experiment"
# All six content-filter categories at maximum strength. PROMPT_ATTACK
# only accepts an input strength; outputStrength MUST be NONE or the API
# rejects the request.
CONTENT_FILTERS = [
    {"type": "SEXUAL",   "inputStrength": "HIGH", "outputStrength": "HIGH"},
    {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
    {"type": "HATE",     "inputStrength": "HIGH", "outputStrength": "HIGH"},
    {"type": "INSULTS",  "inputStrength": "HIGH", "outputStrength": "HIGH"},
    {"type": "MISCONDUCT", "inputStrength": "HIGH", "outputStrength": "HIGH"},
    {"type": "PROMPT_ATTACK", "inputStrength": "HIGH", "outputStrength": "NONE"},
]


def region() -> str:
    r = os.getenv("AWS_REGION")
    if not r:
        sys.exit("AWS_REGION not set in .env")
    return r


def find_existing(bedrock) -> str | None:
    paginator = bedrock.get_paginator("list_guardrails")
    for page in paginator.paginate():
        for g in page.get("guardrails", []):
            if g.get("name") == GUARDRAIL_NAME:
                return g["id"]
    return None


def main() -> None:
    if not (os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")):
        sys.exit("AWS credentials not set in .env (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)")

    bedrock = boto3.client("bedrock", region_name=region())  # control plane

    try:
        gid = find_existing(bedrock)
        if gid:
            print(f"[reuse] guardrail '{GUARDRAIL_NAME}' already exists: {gid}")
        else:
            resp = bedrock.create_guardrail(
                name=GUARDRAIL_NAME,
                description="GuardGap experiment — all filters HIGH.",
                contentPolicyConfig={"filtersConfig": CONTENT_FILTERS},
                blockedInputMessaging="Blocked by guardrail.",
                blockedOutputsMessaging="Blocked by guardrail.",
            )
            gid = resp["guardrailId"]
            print(f"[created] guardrail id: {gid}")

        ver = bedrock.create_guardrail_version(
            guardrailIdentifier=gid,
            description="pinned for experiment run",
        )["version"]
        print(f"[created] guardrail version: {ver}")

    except ClientError as e:
        sys.exit(f"AWS error: {e.response['Error'].get('Code')}: "
                 f"{e.response['Error'].get('Message')}")

    out = {"BEDROCK_GUARDRAIL_ID": gid,
           "BEDROCK_GUARDRAIL_VERSION": ver,
           "region": region()}
    (ROOT / "provisioned.aws.json").write_text(json.dumps(out, indent=2))

    print("\n=== paste into .env ===")
    print(f"BEDROCK_GUARDRAIL_ID={gid}")
    print(f"BEDROCK_GUARDRAIL_VERSION={ver}")
    print("=======================")
    print("wrote provisioned.aws.json")


if __name__ == "__main__":
    main()
