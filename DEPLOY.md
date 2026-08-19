# Deployment

The project is prepared for Render as a FastAPI web service. Render supports deploying directly from GitHub and automatically redeploying when the linked branch changes. Configure the service to use the test branch until the product is reviewed.

Build: `pip install -r requirements.txt`

Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Health check: `/health`

After review, point the production service at `main`.
