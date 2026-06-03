from random import randint
from uuid import uuid4

from locust import HttpUser, between, task


class PlantCareUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        username = f"load_{uuid4().hex[:8]}"
        password = "load-test-pass"
        self.client.post(
            "/api/auth/register/",
            json={"username": username, "email": f"{username}@example.com", "password": password},
        )
        self.client.post("/api/auth/token/", json={"username": username, "password": password})
        species = self.client.get("/api/species/").json()["results"][0]
        plant_response = self.client.post(
            "/api/plants/",
            json={
                "species": species["id"],
                "nickname": f"Load plant {randint(1, 9999)}",
                "location_type": "balcony",
                "notes": "Created by Locust",
            },
        )
        self.plant_id = plant_response.json()["id"]

    @task(4)
    def open_catalog(self):
        self.client.get("/api/species/")

    @task(3)
    def open_my_plants(self):
        self.client.get("/api/plants/")

    @task(2)
    def open_calendar(self):
        self.client.get("/api/care-tasks/")

    @task(1)
    def create_care_log(self):
        self.client.post(
            "/api/care-logs/",
            json={"plant": self.plant_id, "task_type": "water", "notes": "Load test watering"},
        )
