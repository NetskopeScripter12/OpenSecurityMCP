"""Send one real request to the running local API using the token in .env."""
import argparse
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv


def main():
    load_dotenv(Path(__file__).resolve().parent / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", default="/security+ urgent_memo.txt")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    token = os.getenv("SECURITYMCP_API_KEY")
    if not token:
        parser.error("Run python configure.py first")
    with httpx.Client(timeout=310, trust_env=False) as client:
        response = client.post(args.url.rstrip("/") + "/v1/chat",
            headers={"Authorization": f"Bearer {token}"}, json={"message": args.message})
        print(f"HTTP {response.status_code}")
        print(response.text)
        response.raise_for_status()


if __name__ == "__main__":
    main()
