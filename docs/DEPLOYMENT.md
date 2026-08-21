# Deployment

## Render

The repository includes `render.yaml` for a Render Web Service.

1. Create a Render account.
2. Connect GitHub and select `Nomaan-n/AI-pharmacy-assistant`.
3. Select the `main` branch.
4. Review the Blueprint configuration.
5. Add `OPENAI_API_KEY` as a secret if LLM mode is desired.
6. Deploy.

The service exposes `/health` for health checks and `/docs` for OpenAPI documentation.

Never commit API keys or patient information.

## Live-demo checklist

- Verify `/health` returns 200.
- Open `/docs`.
- Test a normal medication-information question.
- Test an urgent symptom question.
- Test a request to stop/change a prescription.
- Verify sources are shown when grounding succeeds.
- Verify the app still gives a safe deterministic response when the LLM key is absent.
