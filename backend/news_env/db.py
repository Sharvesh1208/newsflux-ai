# db.py
import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "news_scrapper")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "articles")

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
collection = db[MONGO_COLLECTION]

print("✅ Connected to MongoDB successfully.")
