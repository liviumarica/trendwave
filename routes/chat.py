from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
from google.cloud import firestore
from extensions import db, mongo_col
import google.generativeai as genai
import os
import json
import logging

chat_bp = Blueprint('chat', __name__)

# Initialize Gemini
try:
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    embed_model = genai.EmbeddingModel(model_name="models/embedding-001")
except Exception as e:
    print(f"Error initializing Gemini or embedding model: {e}")
    gemini_model = None
    embed_model = None

def get_chat_history(user_id):
    try:
        chat_doc = db.collection('chat_sessions').document(user_id).get()
        if chat_doc.exists:
            return chat_doc.to_dict().get('messages', [])
        return []
    except Exception as e:
        print(f"Error getting chat history: {e}")
        return []

def save_chat_history(user_id, messages):
    try:
        chat_ref = db.collection('chat_sessions').document(user_id)
        chat_ref.set({
            'user_id': user_id,
            'messages': messages[-10:],
            'updated_at': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error saving chat history: {e}")

def get_recommendation_context(query):
    if mongo_col is None:
        logging.error("MongoDB collection (mongo_col) is not available.")
        return []
    try:
        if not embed_model:
            logging.error("Embedding model is not initialized.")
            return []

        embedding_response = embed_model.embed_content(content=query, task_type="RETRIEVAL_QUERY")
        query_vector = embedding_response.embedding

        results = list(mongo_col.aggregate([
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "queryVector": query_vector,
                    "path": "embedding",
                    "numCandidates": 100,
                    "limit": 5
                }
            },
            {
                "$project": {
                    "name": 1,
                    "cuisine": 1,
                    "address": 1,
                    "stars": 1,
                    "priceRange": 1,
                    "OutdoorSeating": 1,
                    "DogsAllowed": 1,
                    "HappyHour": 1,
                    "review_count": 1,
                    "borough": 1,
                    "attributes": 1,
                    "score": {"$meta": "vectorSearchScore"},
                    "_id": 0
                }
            }
        ]))
        logging.info(f"MongoDB vector search returned {len(results)} results for query: '{query}'")
        return results
    except Exception as e:
        logging.exception(f"Error during MongoDB vector search for query '{query}':")
        return []

@chat_bp.route('/chat')
@login_required
def chat():
    return render_template('chat.html', username=current_user.email.split('@')[0])

@chat_bp.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    logging.info("--- chat_api: Entered function (outside try block) ---")
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        messages = get_chat_history(current_user.id)

        if not gemini_model:
            return jsonify({'success': False, 'error': 'AI service is currently unavailable'}), 503

        context_docs = get_recommendation_context(user_message)

        context_text = ""
        for r in context_docs:
            addr = r.get("address", {})
            context_text += (
                f"- {r.get('name', 'Unknown')} ({r.get('cuisine', 'unknown cuisine')}), "
                f"Address: {addr.get('street', '')}, {addr.get('zipcode', '')}, "
                f"Rating: {r.get('stars', 'N/A')} stars, Reviews: {r.get('review_count', 'N/A')}, "
                f"Price: {r.get('priceRange', 'N/A')}, Outdoor: {r.get('OutdoorSeating', 'N/A')}, "
                f"DogsAllowed: {r.get('DogsAllowed', 'N/A')}, HappyHour: {r.get('HappyHour', 'N/A')}\n"
            )

        if not context_docs:
            prompt = f"""You are a helpful restaurant assistant.
I could not find specific restaurants in my database for your query: '{user_message}'.
Please ask a more specific question or provide more context (like type of food, price range, location)."""
        else:
            prompt = f"""You are a helpful restaurant assistant.
The user asked: "{user_message}"

Here are some potentially relevant restaurants from the database:
{context_text}

Please answer the user's question using only the data above. Be factual, concise, and suggest options based on context. Do not invent data. If uncertain, ask the user for clarification."""

        logging.info(f"--- chat_api: About to call Gemini with RAG prompt. User message: '{user_message}' ---")
        gemini_response = gemini_model.generate_content(contents=[{"role": "user", "parts": [prompt]}])

        ai_response_text = ""
        try:
            ai_response_text = gemini_response.text
        except Exception as e:
            logging.exception("Error extracting text from Gemini response")
            if gemini_response.prompt_feedback:
                logging.error(f"Prompt feedback: {gemini_response.prompt_feedback}")
                ai_response_text = "I'm sorry, I can't respond to that due to safety guidelines."
            else:
                ai_response_text = "I'm sorry, I encountered an issue generating a response."

        messages.append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.utcnow().isoformat()
        })

        messages.append({
            'role': 'assistant',
            'content': ai_response_text,
            'timestamp': datetime.utcnow().isoformat()
        })

        save_chat_history(current_user.id, messages)

        logging.info("--- chat_api: Successfully processed request, about to return response ---")
        return jsonify({
            'success': True,
            'response': ai_response_text,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logging.exception("--- chat_api: EXCEPTION CAUGHT ---")
        return jsonify({'error': 'Internal Server Error'}), 500
