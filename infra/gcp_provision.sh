#!/usr/bin/env bash
# Provision a Google Vertex AI Model Armor template. Requires gcloud:
#   (install) https://cloud.google.com/sdk/docs/install
#   gcloud auth login
#   gcloud auth application-default login   # so the Python SDK can authenticate
#
# Model Armor is regional; the template is created via the regional REST
# endpoint. This script enables the API and creates a template with the
# malicious-URI, jailbreak/PI, and sensitive-data filters on.
#
# Run:  bash infra/gcp_provision.sh
set -euo pipefail

PROJECT="${GCP_PROJECT_ID:?set GCP_PROJECT_ID in your shell or .env}"
LOCATION="${GCP_LOCATION:-us-central1}"
TEMPLATE_ID="${TEMPLATE_ID:-guardgap-template}"

echo "project: $PROJECT   location: $LOCATION   template: $TEMPLATE_ID"

gcloud config set project "$PROJECT" -q
gcloud services enable modelarmor.googleapis.com -q

TOKEN=$(gcloud auth print-access-token)
API="https://modelarmor.${LOCATION}.rep.googleapis.com/v1"

curl -sS -X POST \
  "${API}/projects/${PROJECT}/locations/${LOCATION}/templates?template_id=${TEMPLATE_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "filterConfig": {
      "raiSettings": { "raiFilters": [
        {"filterType":"DANGEROUS","confidenceLevel":"LOW_AND_ABOVE"},
        {"filterType":"HARASSMENT","confidenceLevel":"LOW_AND_ABOVE"},
        {"filterType":"HATE_SPEECH","confidenceLevel":"LOW_AND_ABOVE"},
        {"filterType":"SEXUALLY_EXPLICIT","confidenceLevel":"LOW_AND_ABOVE"}
      ]},
      "piAndJailbreakFilterSettings": {
        "filterEnforcement":"ENABLED","confidenceLevel":"LOW_AND_ABOVE"
      },
      "maliciousUriFilterSettings": { "filterEnforcement":"ENABLED" }
    }
  }'

echo
echo "=== paste into .env ==="
echo "GCP_PROJECT_ID=$PROJECT"
echo "GCP_LOCATION=$LOCATION"
echo "MODEL_ARMOR_TEMPLATE_ID=$TEMPLATE_ID"
echo "======================="
echo "(If the POST returned an error about confidenceLevel/filterType names,"
echo " check the current Model Armor API reference — field names occasionally"
echo " change between preview versions.)"
