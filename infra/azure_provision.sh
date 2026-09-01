#!/usr/bin/env bash
# Provision an Azure AI Content Safety resource (Prompt Shields + text
# moderation live on the same resource). Requires the Azure CLI:
#   winget install Microsoft.AzureCLI     (then restart the shell)
#   az login
#
# If you'd rather click: Azure Portal -> Create resource -> "Content
# Safety" -> pick a region that supports Prompt Shields (eastus,
# westeurope, ...) -> Create. Then Keys and Endpoint -> copy KEY 1 +
# Endpoint into .env. This script just automates that.
#
# Run:  bash infra/azure_provision.sh
set -euo pipefail

RG="${RG:-guardgap-rg}"
LOCATION="${LOCATION:-eastus}"          # must support Content Safety
NAME="${NAME:-guardgap-contentsafety}"  # 2-64 lowercase/alnum/hyphen, globally unique-ish
SKU="${SKU:-S0}"                        # F0 free tier exists but is rate-limited

echo "resource group: $RG   location: $LOCATION   account: $NAME"

az group create --name "$RG" --location "$LOCATION" -o none

az cognitiveservices account create \
  --name "$NAME" --resource-group "$RG" \
  --kind ContentSafety --sku "$SKU" --location "$LOCATION" \
  --yes -o none

ENDPOINT=$(az cognitiveservices account show \
  --name "$NAME" --resource-group "$RG" \
  --query "properties.endpoint" -o tsv)

KEY=$(az cognitiveservices account keys list \
  --name "$NAME" --resource-group "$RG" \
  --query "key1" -o tsv)

echo
echo "=== paste into .env ==="
echo "AZURE_CONTENT_SAFETY_ENDPOINT=$ENDPOINT"
echo "AZURE_CONTENT_SAFETY_KEY=$KEY"
echo "======================="
