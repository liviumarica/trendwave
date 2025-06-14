from extensions import mongo_col
sample_doc = mongo_col.find_one({"embedding": {"$exists": True}})
if sample_doc:
    print(f"Sample document: {sample_doc}")
    print(f"Embedding length: {len(sample_doc.get('embedding', []))}")
else:
    print("No documents with embedding field found")