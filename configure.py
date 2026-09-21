"""Generate local config once; never overwrite an existing .env."""
import os
import secrets
from pathlib import Path


def main():
    target = Path(__file__).resolve().parent / ".env"
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(".env already exists; keeping your settings.")
        return
    with os.fdopen(fd, "w") as f:
        f.write("OLLAMA_HOST=http://127.0.0.1:11434\nOLLAMA_MODEL=qwen3:8b\n")
        f.write("SECURITYMCP_API_KEY=" + secrets.token_urlsafe(32) + "\n")
    print("Created .env with a random local API token. No paid API key needed.")


if __name__ == "__main__":
    main()
