# Public deployment

## Prepared configuration

This directory contains a multi-stage Dockerfile and render.yaml for one public Render web service. React is built first, then served by FastAPI from the same origin. The reference workbook is included. The answer key and uploaded workbooks are not deployed as static files.

## Publish

1. Sign in to GitHub and create a repository containing the contents of this onelab directory at its root. Exclude node_modules, web-build, caches and credentials using .gitignore.
2. Sign in to Render and choose New > Blueprint. Connect that repository.
3. Review the ledgerlens-onelab web service and confirm the Free instance selected in render.yaml. Deploy the Blueprint.
4. Wait for a successful deployment. Copy the actual public URL shown by Render; no deployment URL has been created yet.
5. Check /api/health, download the reference workbook, upload it for October 2026, inspect evidence, and export a report.
6. Test the public URL in a signed-out browser before submitting it.

Render Free services can spin down after inactivity, making the next request slow. Open the app before a demonstration and allow startup time. See https://render.com/docs/free.

If the Git repository contains the parent AI Fitness folder instead, the project lives under onelab/. Set that as the service root directory and select the Blueprint path onelab/render.yaml when importing.

## Current blocker

The current workspace has no Git remote or authenticated hosting connection. Deployment needs the user's hosting account connection and a repository URL. Do not share passwords or paste API keys into chat; use the provider's sign-in/connection flow.
