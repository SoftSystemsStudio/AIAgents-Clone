Vercel Deployment Setup
======================

This project includes an optional GitHub Actions workflow `.github/workflows/vercel-deploy.yml` that will deploy the built `build/` directory to Vercel on push to `main`.

Required repository secrets
- `VERCEL_TOKEN` — a Vercel Personal Token with project deploy permissions.
- `VERCEL_ORG_ID` — the Vercel organization ID for your account.
- `VERCEL_PROJECT_ID` — the Vercel project ID for this repository.

How to create these values
1. Go to https://vercel.com/account and create a Personal Token.
2. On your Vercel project, open Settings → General → Project ID (copy the Project ID).
3. For the Org ID, open your Vercel Organization settings and copy the Organization ID.

Add secrets to GitHub
1. In your GitHub repository, go to Settings → Secrets → Actions.
2. Add the three secrets above (`VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`).

Notes
- The deploy workflow uses `amondnet/vercel-action` which will perform the deploy using the provided token and IDs.
- If you prefer preview deployments only, you can change the action arguments in the workflow.
