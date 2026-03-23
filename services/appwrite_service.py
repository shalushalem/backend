from appwrite.client import Client
from appwrite.services.account import Account
from appwrite.services.databases import Databases

# 🔐 Initialize client
client = Client()
client.set_endpoint("https://cloud.appwrite.io/v1")  # change if self-hosted
client.set_project("69958f25003190519213")

# Services
account = Account(client)
databases = Databases(client)