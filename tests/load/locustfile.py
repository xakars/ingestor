import random
import time
import uuid

from locust import HttpUser, between, task


class IngestorUser(HttpUser):
    wait_time = between(0.1, 0.5)
    host = "http://localhost:8000"

    def on_start(self):
        self.token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyX3VzZXIiLCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJyb2xlIjoidXNlciIsInBlcm1pc3Npb25zIjpbInJlYWQiLCJ3cml0ZSJdLCJleHAiOjE3Nzc3NzI3MzEsImlhdCI6MTc3Nzc3MDkzMSwidHlwZSI6ImFjY2VzcyJ9._Rjln53AixVqntL67oJCzh6o7bPp78sRcAeG0LCeUQQ"
        self.device_id = str(uuid.uuid4())

    @task(3)
    def send_metrics(self):
        self.client.post(
            "/api/v1/metrics",
            json={
                "device_id": self.device_id,
                "timestamp": int(time.time()),
                "metrics": [
                    {"name": "cpu_usage", "value": random.uniform(0, 100)},
                    {"name": "memory_usage", "value": random.uniform(0, 100)},
                ],
            },
            headers={"Authorization": self.token},
            name="/api/v1/metrics",
        )

    @task(1)
    def check_health(self):
        """Проверка health endpoint"""
        self.client.get("/health/live", name="/health/live")
