import logging
import os
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from google.cloud import firestore
from google import genai
from google.genai import types
import logging

from extensions import db, mongo_col

# Create a module-level logger
logger = logging.getLogger(__name__)

# Initialize client as None - will be lazy-loaded
_client = None

def get_genai_client():
    """Lazy-load and return the Google GenAI client."""
    global _client
    
    if _client is None:
        try:
            _client = genai.Client(
                vertexai=True,
                project=os.getenv('GOOGLE_CLOUD_PROJECT'),
                location=os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
            )
            logger.info("Successfully initialized Google GenAI client with Vertex AI")
        except Exception as e:
            logger.error(f"Failed to initialize Google GenAI client: {str(e)}")
            _client = None
    
    return _client

chat_bp = Blueprint("chat", __name__)

# -----------------------------------------------------------------------------
#  Helpers: Firestore chat history
# -----------------------------------------------------------------------------

def _history_doc(uid):
    return db.collection("chat_sessions").document(str(uid))


def get_chat_history(uid):
    try:
        snap = _history_doc(uid).get()
        return snap.to_dict().get("messages", []) if snap.exists else []
    except Exception as exc:
        logging.warning("Firestore history error: %s", exc)
        return []


def save_chat_history(uid, msgs):
    try:
        _history_doc(uid).set({
            "user_id": str(uid),
            "messages": msgs[-10:],
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
    except Exception as exc:
        logging.error("Failed to save history: %s", exc)

# -----------------------------------------------------------------------------
#  Vector search helper
# -----------------------------------------------------------------------------

def vector_search(query: str):
    if mongo_col is None:
        return []

    client = get_genai_client()
    if client is None:
        logger.error("Google GenAI client not initialized")
        return []
        
    embed_model = current_app.config["EMBED_MODEL"]
    
    try:
        response = client.models.embed_content(
            model=embed_model,
            contents=[query],
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY"
            )
        )
        
        # Extract the embedding vector as a list of floats
        if hasattr(response, 'embedding') and response.embedding:
            vec = response.embedding.values
        elif hasattr(response, 'embeddings') and response.embeddings:
            vec = response.embeddings[0].values
        else:
            logger.error("Unexpected response format from embed_content")
            return []
        logger.info(f"Generated query vector length: {len(vec)}")    
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return []

    pipeline = [
        {"$vectorSearch": {
            "index": "vector_index_1",
            "queryVector": vec,
            "path": "embedding",
            "numCandidates": 100,
            "limit": 5,
        }},
        {"$project": {
            "name": 1, "cuisine": 1, "address": 1, "stars": 1,
            "priceRange": 1, "OutdoorSeating": 1, "DogsAllowed": 1,
            "score": {"$meta": "vectorSearchScore"}, "_id": 0,
        }}
    ]
    try:
        results = list(mongo_col.aggregate(pipeline))
        logger.info(f"Vector search returned {len(results)} candidates: {results}")
        return results
    except Exception as e:
        logger.error(f"Error in MongoDB vector search: {str(e)}")
        return []
# -----------------------------------------------------------------------------
#  Routes
# -----------------------------------------------------------------------------

@chat_bp.route("/chat")
@login_required
def chat():
    return render_template("chat.html", username=current_user.email.split("@")[0])


@chat_bp.route("/api/chat", methods=["POST"])
@login_required
def chat_api():
    try:
        data = request.get_json(force=True)
        user_msg = data.get("message", "").strip()
        if not user_msg:
            return jsonify({"success": False, "error": "Empty message"}), 400

        history = get_chat_history(current_user.id)
        candidates = vector_search(user_msg)
        logger.info(f"Candidates from vector search: {candidates}")
        if candidates:
            ctx = "\n".join(
                f"- {c['name']} ({c['cuisine']}), ⭐{c.get('stars', 'N/A')} — "
                f"Outdoor: {c.get('OutdoorSeating', 'N/A')}" for c in candidates)
            prompt = (
                f"You are a helpful restaurant assistant.\n"
                f"User: {user_msg}\n"
                f"Here are some possible restaurants:\n{ctx}\n"
                f"Answer with best recommendations using only this data.")
        else:
            prompt = (f"You are a helpful restaurant assistant. User asks: '{user_msg}'. "
                      f"No matching restaurants found — politely ask for more details.")

        logger.info(f"Generated prompt: {prompt}")
        text_model = current_app.config["TEXT_MODEL"]
        client = get_genai_client()
        if client is None:
            return jsonify({"success": False, "error": "AI service not initialized"}), 500
        
        response = client.models.generate_content(
            model=text_model,
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        # Extract the response text
        if hasattr(response, 'text'):
            answer = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            answer = response.candidates[0].content.parts[0].text
        else:
            return jsonify({"success": False, "error": "Unexpected response format from AI service"}), 500
            
        # Append and save history
        history += [
            {"role": "user", "content": user_msg, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": answer, "timestamp": datetime.utcnow().isoformat()},
        ]
        save_chat_history(current_user.id, history)

        return jsonify({"success": True, "response": answer})
        
    except Exception as e:
        logger.error(f"Error in chat_api: {str(e)}")
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500
