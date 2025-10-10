from dotenv import load_dotenv
import os
import requests

load_dotenv()
username = os.getenv('USERNAME')
password = os.getenv('PASSWORD')
API = os.getenv('API')


class Platform:
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def login(self):
        res = requests.post(f"{API}/api/v1/login", json={"username": self.username, "password": self.password})
        print(f"Logging in with username: {self.username} and password: {self.password}")
