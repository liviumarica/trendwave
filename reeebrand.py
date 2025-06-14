from extensions import mongo_col
from google import genai
import os
import logging
from datetime import datetime

# Set up logging to a file
log_filename = f"reembed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_filename), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize the GenAI client
try:
    client = genai.Client(
        vertexai=True,
        project=os.getenv('GOOGLE_CLOUD_PROJECT'),
        location=os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
    )
    logger.info("Successfully initialized Google GenAI client")
except Exception as e:
    logger.error(f"Failed to initialize Google GenAI client: {e}")
    raise

embed_model = "gemini-embedding-001"

# Fetch all documents
for doc in mongo_col.find({"embedding": {"$exists": True}}):
    try:
        text_to_embed = f"{doc.get('name', '')} {doc.get('cuisine', '')} {doc.get('address', {}).get('street', '')} {doc.get('borough', '')}"
        logger.info(f"Embedding text for {doc['name']}: {text_to_embed}")
        response = client.models.embed_content(
            model=embed_model,
            contents=[text_to_embed],
            config=genai.types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        if hasattr(response, 'embeddings') and response.embeddings:
            new_embedding = response.embeddings[0].values
            logger.info(f"Embedding values for {doc['name']}: {new_embedding[:10]}... (length: {len(new_embedding)})")
            mongo_col.update_one(
                {"_id": doc["_id"]},
                {"$set": {"embedding": new_embedding}}
            )
            logger.info(f"Updated embedding for {doc['name']} (ID: {doc['_id']})")
        else:
            logger.warning(f"No embeddings found in response for {doc['name']} (ID: {doc['_id']})")
    except Exception as e:
        logger.error(f"Error updating {doc['name']} (ID: {doc['_id']}): {e}")

logger.info("Re-embedding process completed")