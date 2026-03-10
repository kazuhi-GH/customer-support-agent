import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
AGENT_NAME = os.getenv("AGENT_NAME", "customer-support-agent")
