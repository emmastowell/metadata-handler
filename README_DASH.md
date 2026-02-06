# Metadata Creator - Dash App

A TfL-styled Plotly Dash application for generating metadata from data files using a Databricks Model Serving (Claude) endpoint.

## Features

- **TfL-styled interface**: Transport for London roundel logo and colour scheme
- **File upload**: CSV, Excel, JSON, and text files (up to 100MB)
- **AI-powered metadata generation**: Connects to Databricks Model Serving
- **Configurable prompt**: JSON schema and LLM instructions in a separate file
- **Configuration via .env**: No hardcoded profile names, URLs, or model names in the repo

## Prerequisites

- Python 3.11+
- A Databricks workspace with a Model Serving endpoint (e.g. Claude)
- Databricks CLI installed and authenticated (for local development and deploy)

## Configuration

All personal and environment-specific settings live in a **`.env`** file. The `databricks.yml` file does **not** contain any workspace URLs or model/endpoint names; those are read from `.env` at runtime and when deploying. **Do not commit `.env` to version control.**

### 1. Create your `.env` file

Copy the example and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABRICKS_CONFIG_PROFILE` | Databricks CLI profile name (from `databricks auth login`) | `my-profile` |
| `DATABRICKS_HOST` | Databricks workspace URL | `https://your-workspace.cloud.databricks.com` |
| `DATABRICKS_SERVING_ENDPOINT` | Model Serving endpoint name | `databricks-claude-opus-4-5` |

- **Local run**: the app uses these to connect to your workspace and the chosen endpoint.
- **Deploy**: the same values are passed into the bundle so the bundle knows which workspace and endpoint to use (see [Deploy to Databricks](#deploy-to-databricks)).

### 2. Authenticate with Databricks (local and deploy)

Use the same profile name as in `.env`:

```bash
databricks auth login --profile YOUR_PROFILE_NAME
```

## Metadata prompt (LLM instructions)

The JSON schema and instructions sent to the LLM are in **`metadata_prompt.txt`** in the project root. You can edit this file to change the target JSON structure and behaviour (e.g. how many questions at a time). The app loads it at startup; restart the app after changes.

## Local development

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Ensure `.env` exists and contains `DATABRICKS_CONFIG_PROFILE`, `DATABRICKS_HOST`, and `DATABRICKS_SERVING_ENDPOINT` (see [Configuration](#configuration)).

### 3. Run the app

```bash
python app.py
```

The app will be available at http://localhost:8050

## Deploy to Databricks

Workspace URL and model/endpoint name are **not** stored in `databricks.yml` (only placeholders). They are taken from your `.env` when you deploy.

### Option A: Deploy script (recommended)

With `.env` configured:

```bash
./deploy.sh
```

The script loads `.env`, writes `.databricks/bundle/dev/variable-overrides.json` from your `DATABRICKS_HOST` and `DATABRICKS_SERVING_ENDPOINT`, then runs `bundle validate` and `bundle deploy`. The `.databricks/` directory is gitignored.

### Option B: Manual deploy

Create variable overrides from your `.env`, then deploy:

```bash
set -a && source .env && set +a
mkdir -p .databricks/bundle/dev
printf '%s\n' "{\"workspace_host\": \"$DATABRICKS_HOST\", \"serving_endpoint_name\": \"$DATABRICKS_SERVING_ENDPOINT\"}" > .databricks/bundle/dev/variable-overrides.json
databricks bundle validate --profile "$DATABRICKS_CONFIG_PROFILE"
databricks bundle deploy --profile "$DATABRICKS_CONFIG_PROFILE"
```

### If you see "config host mismatch"

The Databricks CLI resolves auth **before** applying variable overrides, so `validate`/`deploy` can fail when only placeholders are in `databricks.yml`. **Workaround:** set the variable defaults in `databricks.yml` to your real values (under `variables.workspace_host.default` and `variables.serving_endpoint_name.default`). Use your `.env` values; you can do this in a private or deploy-only copy so the main repo keeps placeholder defaults.

### Start the app after deploy

```bash
databricks bundle run metadata_creator_app --profile YOUR_PROFILE_NAME
```

Or in the Databricks UI: **Apps** → your app → **Start**. The app URL will be shown in the CLI or in the Apps UI.

## Project layout

```
Metadata_Creator_App/
├── app.py              # Main Dash application
├── app.yaml            # Databricks App runtime config
├── databricks.yml      # Bundle config (placeholder vars; real values from .env via variable-overrides or defaults)
├── deploy.sh           # Deploy using .env (sources .env and runs bundle deploy)
├── metadata_prompt.txt # JSON schema + LLM instructions
├── requirements.txt   # Python dependencies
├── .env                # Your config (create from .env.example; do not commit)
├── .env.example        # Example env vars (no real values)
└── README_DASH.md      # This file
```

## File support

| Format | Extensions | Max size |
|--------|------------|----------|
| CSV    | .csv       | 100MB    |
| Excel  | .xlsx, .xls | 100MB  |
| JSON   | .json      | 100MB    |
| Text   | .txt, .dat | 100MB   |

## Troubleshooting

### "DATABRICKS_SERVING_ENDPOINT is not set"
- Add `DATABRICKS_SERVING_ENDPOINT=your-endpoint-name` to `.env` for local runs.
- On Databricks Apps it is set from the bundle; redeploy with `./deploy.sh` (or the manual command) so the bundle has the right endpoint.

### "Error calling model"
- Check the endpoint name in `.env`. Confirm the endpoint exists and the app has CAN_QUERY:  
  `databricks serving-endpoints get --name YOUR_ENDPOINT --profile YOUR_PROFILE`

### "Metadata prompt file not found"
- Ensure `metadata_prompt.txt` is in the same directory as `app.py`. Do not exclude it via `.databricksignore`.

### Invalid access token / wrong host
- Use only values from `.env` for profile and host. Run  
  `databricks auth login --profile YOUR_PROFILE_NAME`  
  and set `DATABRICKS_CONFIG_PROFILE` and `DATABRICKS_HOST` in `.env` accordingly.

### Bundle validate/deploy fails (missing variable or "config host mismatch")
- Ensure `.env` has `DATABRICKS_HOST` and `DATABRICKS_SERVING_ENDPOINT`. Run `./deploy.sh` so it writes `.databricks/bundle/dev/variable-overrides.json` from `.env`.
- If you still get **config host mismatch**, the CLI may not apply overrides before auth. Set the variable defaults in `databricks.yml` to your `DATABRICKS_HOST` and `DATABRICKS_SERVING_ENDPOINT` (see [Deploy](#deploy-to-databricks)).

## Licence

This is a custom application for TfL metadata generation.
