"""
Load test for the chat endpoint, using Locust.

This exists to answer an interview question you WILL get: "how do you know
it scales?" -- run this against a staging deployment and bring the numbers
(requests/sec, p95 latency, error rate at N concurrent users) to the table.

Usage:
    pip install locust --break-system-packages
    locust -f scripts/load_test.py --host http://localhost:8000

Then open http://localhost:8089, set concurrent users + spawn rate, and watch
p50/p95 latency and failure rate as load increases. Rate limiting (20
req/min/user by default) means many simulated users is more realistic than
one user hammering the endpoint -- this script logs each simulated user in
as its own account for exactly that reason.
"""
import random
import uuid

from locust import HttpUser, between, task

SAMPLE_QUESTIONS = [
    "What is the refund window for a subscription?",
    "Does the product support single sign-on?",
    "What happens to my data if I cancel my plan?",
    "Is there a free tier available?",
    "What are the standard working hours?",
]


class DocklightUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        email = f"loadtest-{uuid.uuid4().hex[:10]}@example.com"
        response = self.client.post(
            "/api/auth/signup",
            json={"email": email, "password": "LoadTest1234"},
            name="/api/auth/signup",
        )
        self.token = response.json().get("access_token", "") if response.status_code == 200 else ""
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task
    def ask_a_question(self):
        if not self.token:
            return
        self.client.post(
            "/api/chat/query",
            json={"question": random.choice(SAMPLE_QUESTIONS)},
            headers=self.headers,
            name="/api/chat/query",
        )

    @task(2)
    def list_documents(self):
        if not self.token:
            return
        self.client.get("/api/documents", headers=self.headers, name="/api/documents")
