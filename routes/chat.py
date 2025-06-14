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

    # Get the GenAI client
    client = get_genai_client()
    if client is None:
        logger.error("Google GenAI client not initialized")
        return []
        
    embed_model = current_app.config["EMBED_MODEL"]
    
    try:
        # Generate embeddings using the Google GenAI client with Vertex AI
        response = client.models.embed_content(
            model=embed_model,
            contents=[query],
            config=types.EmbedContentConfig(
                task_type="retrieval_query"
            )
        )
        
        # Extract the embedding vector from the response
        if hasattr(response, 'embedding') and response.embedding:
            vec = response.embedding
        elif hasattr(response, 'embeddings') and response.embeddings:
            vec = response.embeddings[0]
        else:
            logger.error("Unexpected response format from embed_content")
            return []
            
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return []

    pipeline = [
        {"$vectorSearch": {
            "index": "vector_index",
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
    return list(mongo_col.aggregate(pipeline))

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
    data = request.get_json(force=True)
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"success": False, "error": "empty"}), 400

    history = get_chat_history(current_user.id)
    candidates = vector_search(user_msg)

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

    text_model = current_app.config["TEXT_MODEL"]
    
    # Get the GenAI client
    client = get_genai_client()
    if client is None:
        logger.error("Google GenAI client not initialized")
        return jsonify({"success": False, "response": "Error initializing AI service"}), 500
    
    try:
        # Generate content using the client with the specified model
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
            logger.error("Unexpected response format from generate_content")
            return jsonify({"success": False, "response": "Unexpected response format from AI service"}), 500
            
        # append and save history
        history += [
            {"role": "user", "content": user_msg, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": answer, "timestamp": datetime.utcnow().isoformat()},
        ]
        save_chat_history(current_user.id, history)

        return jsonify({"success": True, "response": answer})
        
    except Exception as e:
        logger.error(f"Error generating content: {str(e)}")
        return jsonify({"success": False, "response": f"Error generating response: {str(e)}"}), 500
