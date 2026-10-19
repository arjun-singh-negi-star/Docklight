"""
Seeds a demo account with the sample documents in scripts/sample_docs, so you can try the full
pipeline (upload -> Celery worker -> Pinecone -> chat) without hunting for files.

The API requires auth, so this signs up the demo user (or logs in if it already exists) first.

Usage:
    pip install requests
    python scripts/seed_fake_data.py --api http://localhost:8000 --email demo@example.com --password DemoPass123
"""
import argparse
import pathlib

import requests

SAMPLE_DIR = pathlib.Path(__file__).parent / "sample_docs"


def get_token(api_base: str, email: str, password: str) -> str:
    creds = {"email": email, "password": password}
    response = requests.post(f"{api_base}/api/auth/signup", json=creds, timeout=30)
    if response.status_code == 409:  # account already exists -> log in instead
        response = requests.post(f"{api_base}/api/auth/login", json=creds, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def seed(api_base: str, email: str, password: str) -> None:
    files = sorted(SAMPLE_DIR.glob("*.txt"))
    if not files:
        print(f"No sample files found in {SAMPLE_DIR}")
        return

    headers = {"Authorization": f"Bearer {get_token(api_base, email, password)}"}
    for path in files:
        with open(path, "rb") as f:
            response = requests.post(
                f"{api_base}/api/documents/upload",
                files={"file": (path.name, f, "text/plain")},
                headers=headers,
                timeout=120,
            )
        print(f"{path.name} -> {response.status_code} {response.json()}")
    print("Queued. Log in to the UI with the same account; documents turn 'indexed' in a few seconds.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:8000", help="Base URL of the running backend")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True, help="min 8 characters")
    args = parser.parse_args()
    seed(args.api, args.email, args.password)
