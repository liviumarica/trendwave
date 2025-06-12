from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
from google.cloud import firestore
from extensions import db, mongo_col # Import mongo_col for MongoDB access
import google.generativeai as genai
import os
import json
import logging

# Create blueprint
chat_bp = Blueprint('chat', __name__)

# Initialize Gemini
try:
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"Error initializing Gemini in chat routes: {e}")
    gemini_model = None

def get_chat_history(user_id):
    """Retrieve chat history for a user"""
    try:
        chat_doc = db.collection('chat_sessions').document(user_id).get()
        if chat_doc.exists:
            return chat_doc.to_dict().get('messages', [])
        return []
    except Exception as e:
        print(f"Error getting chat history: {e}")
        return []

def save_chat_history(user_id, messages):
    """Save chat history for a user"""
    try:
        # Keep only the last 10 messages to prevent excessive storage
        chat_ref = db.collection('chat_sessions').document(user_id)
        chat_ref.set({
            'user_id': user_id,
            'messages': messages[-10:],
            'updated_at': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error saving chat history: {e}")

# Helper function to get recommendation context from MongoDB
def get_recommendation_context(query):
    """Retrieve restaurant context from MongoDB using vector search."""
    if mongo_col is None: # Changed from 'if not mongo_col' to 'if mongo_col is None'
        logging.error("MongoDB collection (mongo_col) is not available.")
        return []
    try:
        # Placeholder for actual embedding generation from the query
        # In a real scenario, you would convert the 'query' into a vector embedding
        # For example, using a sentence transformer or another Gemini model endpoint
        placeholder_embedding = [0.01] * 256  # Example: 256-dimensional embedding

        results = list(mongo_col.aggregate([
            {
                "$vectorSearch": {
                    "index": "vector_index", # Make sure this index exists in your MongoDB collection
                    "queryVector": placeholder_embedding,
                    "path": "embedding", # The field in your documents that contains the vector
                    "numCandidates": 100,
                    "limit": 5 # Number of top results to retrieve
                }
            },
            {
                "$project": {
                    "name": 1,
                    "cuisine": 1,
                    "attributes": 1,
                    "_id": 0, # Exclude the _id field
                    "score": {"$meta": "vectorSearchScore"}
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
    """Render the chat interface"""
    return render_template('chat.html', username=current_user.email.split('@')[0])

@chat_bp.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """Handle chat messages and return AI responses"""
    logging.info("--- chat_api: Entered function (outside try block) ---")
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Get chat history (messages before current user input)
        messages = get_chat_history(current_user.id)
        
        # Generate response using Gemini
        if not gemini_model:
            return jsonify({
                'success': False,
                'error': 'AI service is currently unavailable'
            }), 503
            
        # Get recommendation context from MongoDB
        context_docs = get_recommendation_context(user_message)
        context_text = "\n".join(
            f"- {r.get('name', 'Unknown Restaurant')} ({r.get('cuisine', 'unknown cuisine')}): Attributes: {r.get('attributes', 'N/A')}. Search Score: {r.get('score',0):.2f}"
            for r in context_docs
        )

        if not context_docs:
            logging.info("No context documents found from MongoDB for the query.")
            # Fallback prompt if no context is found, or handle as an error/specific message
            prompt = f"""You are a helpful restaurant assistant.
I could not find specific restaurants in my database for your query: '{user_message}'.
Can you please provide more details or try a different search? For example, tell me your location, budget, and preferred type of food."""
        else:
            prompt = f"""You are a helpful restaurant assistant.
The user asked: "{user_message}"

Based on my database, here are some potentially relevant restaurants:
{context_text}

Please analyze these options and provide a helpful recommendation or answer based *only* on this information. If the provided options don't seem to fit the user's query well, acknowledge that and perhaps ask for clarification. Do not invent restaurants or details not present in the provided list."""

        logging.info(f"--- chat_api: About to call Gemini with RAG prompt. User message: '{user_message}' ---")
        # Use generate_content for RAG, not start_chat
        gemini_response = gemini_model.generate_content(contents=[{"role": "user", "parts": [prompt]}])
        ai_response_text = ""
        try:
            ai_response_text = gemini_response.text
        except Exception as e:
            logging.exception("Error extracting text from Gemini response (candidates might be empty or malformed)")
            # Check for blocked prompts or safety issues
            if gemini_response.prompt_feedback:
                logging.error(f"Prompt feedback: {gemini_response.prompt_feedback}")
                ai_response_text = "I'm sorry, I can't respond to that due to safety guidelines."
            else:
                ai_response_text = "I'm sorry, I encountered an issue generating a response."

        # Add current user message to messages list for saving to Firestore
        messages.append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Add assistant's RAG response to messages list for saving to Firestore
        messages.append({
            'role': 'assistant',
            'content': ai_response_text,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Save updated chat history (user query + RAG AI response) to Firestore
        save_chat_history(current_user.id, messages)
        
        logging.info("--- chat_api: Successfully processed request, about to return response ---")
        return jsonify({
            'success': True,
            'response': ai_response_text,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logging.exception("--- chat_api: EXCEPTION CAUGHT --- An error occurred in the chat API:")
        # Return a very simple error message to avoid issues with jsonify itself
        return jsonify({'error': 'Internal Server Error'}), 500
