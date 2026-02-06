#!/usr/bin/env bash
# Deploy the app to Databricks using variables from .env
# Requires: .env with DATABRICKS_CONFIG_PROFILE, DATABRICKS_HOST, DATABRICKS_SERVING_ENDPOINT

set -e
cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
  echo "Error: .env not found. Copy .env.example to .env and set your values."
  exit 1
fi

# Load .env and export for this script (no spaces around =)
set -a
source .env
set +a

for key in DATABRICKS_CONFIG_PROFILE DATABRICKS_HOST DATABRICKS_SERVING_ENDPOINT; do
  if [[ -z "${!key}" ]]; then
    echo "Error: $key is not set in .env"
    exit 1
  fi
done

# Write bundle variable overrides from .env so validate/deploy use your workspace and endpoint.
# (.databricks/ is gitignored; the CLI resolves auth using these values.)
mkdir -p .databricks/bundle/dev
printf '%s\n' "{
  \"workspace_host\": \"$DATABRICKS_HOST\",
  \"serving_endpoint_name\": \"$DATABRICKS_SERVING_ENDPOINT\"
}" > .databricks/bundle/dev/variable-overrides.json

echo "Deploying to $DATABRICKS_HOST with endpoint $DATABRICKS_SERVING_ENDPOINT (profile: $DATABRICKS_CONFIG_PROFILE)"
databricks bundle validate --profile "$DATABRICKS_CONFIG_PROFILE"
databricks bundle deploy --profile "$DATABRICKS_CONFIG_PROFILE"

echo "Deployment complete. Start the app with:"
echo "  databricks bundle run metadata_creator_app --profile $DATABRICKS_CONFIG_PROFILE"
