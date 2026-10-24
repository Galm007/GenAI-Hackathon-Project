import os

# app.config requires these at import time; tests never reach the real services.
for key, value in {
    "SUPABASE_URL": "http://localhost:54321",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role",
    "ZETARIS_AGENT_PASSWORD": "test-zetaris",
    "ANTHROPIC_API_KEY": "test-anthropic",
}.items():
    os.environ.setdefault(key, value)
