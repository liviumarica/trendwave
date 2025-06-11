import os
from pymongo import MongoClient
from datasets import load_dataset
from bson import json_util

uri = os.environ.get('MONGODB_URI')
if not uri:
    raise RuntimeError("❗ MONGODB_URI nu a fost setată!")
client = MongoClient(uri)
db = client["whatscooking"]
col = db["restaurants"]

dataset = load_dataset("MongoDB/whatscooking.restaurants", split="train")
batch = []
for rest in dataset:
    batch.append(json_util.loads(json_util.dumps(rest)))
    if len(batch) >= 1000:
        col.insert_many(batch)
        print("➡️ 1000 docs uploaded")
        batch.clear()
if batch:
    col.insert_many(batch)
    print("➡️ Final batch uploaded")
print("✅ Data ingest complete")
