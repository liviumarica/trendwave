"""
Chat routes for the TrendWave application.
Handles chat-related functionality including message processing and response generation.
"""
import os
import logging
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from google.cloud import firestore
from extensions import db, mongo_col
from models.user import User

# Initialize the chat blueprint
chat_bp = Blueprint('chat', __name__)

def get_chat_history(user_id):
    """
    Retrieve chat history for a user from Firestore.
    Returns an empty list if no history exists or if an error occurs.
    """
    if not user_id:
        logging.warning("No user_id provided to get_chat_history")
        return []
        
    try:
        chat_ref = db.collection('chat_sessions').document(str(user_id))
        chat_doc = chat_ref.get()
        
        if not chat_doc.exists:
            logging.info(f"No chat history found for user {user_id}")
            return []
            
        chat_data = chat_doc.to_dict()
        messages = chat_data.get('messages', [])
        
        # Ensure we're returning a list and filter out any invalid messages
        if not isinstance(messages, list):
            logging.warning(f"Chat history for user {user_id} is not a list: {messages}")
            return []
            
        # Filter out any invalid message entries
        valid_messages = []
        for msg in messages:
            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                valid_messages.append({
                    'role': msg.get('role', ''),
                    'content': msg.get('content', ''),
                    'timestamp': msg.get('timestamp', datetime.utcnow().isoformat())
                })
        
        logging.info(f"Retrieved {len(valid_messages)} messages from chat history for user {user_id}")
        return valid_messages
        
    except Exception as e:
        logging.error(f"Error getting chat history for user {user_id}: {str(e)}", exc_info=True)
        return []

def save_chat_history(user_id, messages):
    """
    Save chat history for a user to Firestore.
    
    Args:
        user_id: The ID of the user
        messages: List of message dictionaries to save
    """
    if not user_id:
        logging.error("Cannot save chat history: No user_id provided")
        return False
        
    if not messages or not isinstance(messages, list):
        logging.error(f"Cannot save chat history for user {user_id}: Invalid messages format")
        return False
        
    try:
        # Ensure we don't save too many messages
        messages_to_save = messages[-10:]  # Keep only the last 10 messages
        
        # Prepare the document data
        chat_data = {
            'user_id': str(user_id),
            'messages': messages_to_save,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'message_count': len(messages_to_save)
        }
        
        # Save to Firestore
        doc_ref = db.collection('chat_sessions').document(str(user_id))
        doc_ref.set(chat_data)
        
        logging.info(f"Successfully saved {len(messages_to_save)} messages for user {user_id}")
        return True
        
    except Exception as e:
        logging.error(f"Error saving chat history for user {user_id}: {str(e)}", exc_info=True)
        return False

def get_recommendation_context(query):
    """
    Get relevant restaurant recommendations based on the user's query using vector search.
    
    Args:
        query: The user's search query
        
    Returns:
        List of restaurant documents matching the query, or empty list if no results or error
    """
    if not query or not isinstance(query, str):
        logging.warning("Invalid query provided to get_recommendation_context")
        return []
        
    if mongo_col is None:
        logging.error("MongoDB collection not available. Check your MongoDB connection.")
        return []
        
    try:
        logging.info(f"Generating embeddings for query: '{query}'")
        
        # Generate embedding vector for the query
        embeddings = current_app.embed_model.get_embeddings([query])
        if not embeddings or not hasattr(embeddings[0], 'values'):
            logging.error("Failed to generate embeddings for query")
            return []
            
        query_vec = embeddings[0].values
        logging.info("Successfully generated query vector")

        # Define the vector search pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "queryVector": query_vec,
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
                    "score": {"$meta": "vectorSearchScore"}, 
                    "_id": 0
                }
            },
            {
                "$addFields": {
                    "score": {"$round": ["$score", 4]}
                }
            }
        ]
        
        logging.info("Executing MongoDB aggregation pipeline...")
        cursor = mongo_col.aggregate(pipeline)
        results = list(cursor)
        
        logging.info(f"MongoDB returned {len(results)} results for query: '{query}'")
        if results:
            logging.debug(f"Sample result: {results[0]}")
            
        return results
        
    except Exception as e:
        logging.error(f"Error during vector search for '{query}': {str(e)}", exc_info=True)
        return []

@chat_bp.route('/chat')
@login_required
def chat():
    return render_template('chat.html', username=current_user.email.split('@')[0])

@chat_bp.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        logging.info(f"Received chat request with data: {data}")
        
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400

        try:
            # Check if models are initialized
            if not hasattr(current_app, 'gemini_model') or not current_app.gemini_model:
                error_msg = "Text generation model is not initialized. Please check the server logs for details."
                current_app.logger.error(error_msg)
                return jsonify({
                    'success': False,
                    'error': 'AI service is not available',
                    'details': error_msg,
                    'model_status': 'not_initialized'
                }), 500
            
            if not hasattr(current_app, 'embed_model') or not current_app.embed_model:
                error_msg = "Text embedding model is not initialized. Please check the server logs for details."
                current_app.logger.error(error_msg)
                return jsonify({
                    'success': False,
                    'error': 'AI service is not available',
                    'details': error_msg,
                    'model_status': 'not_initialized'
                }), 500
                
            messages = get_chat_history(current_user.id)
            context_docs = get_recommendation_context(user_message)

            # Build prompt
            if not context_docs:
                prompt = f"You are a restaurant assistant. No relevant restaurants found for '{user_message}'. Ask for more details to provide better recommendations."
                logging.info("No context docs found, using fallback prompt")
            else:
                ctx = "\n".join(
                    f"- {r.get('name', 'Unnamed')} ({r.get('cuisine', 'Unknown cuisine')}), "
                    f"Address: {r.get('address', {}).get('street', 'N/A')}, {r.get('address', {}).get('zipcode', '')}, "
                    f"Rating: ⭐ {r.get('stars', 'N/A')}, "
                    f"Price: {r.get('priceRange', 'N/A')}, "
                    f"Outdoor: {r.get('OutdoorSeating', 'N/A')}"
                    for r in context_docs
                )
                prompt = (
                    f"You are a helpful restaurant assistant.\n"
                    f"User asked: \"{user_message}\"\n"
                    f"Here are some restaurant candidates that might match:\n{ctx}\n"
                    f"Please provide a helpful response based on these options. If the user is looking for something specific "
                    f"that's not in these options, politely suggest they try a different search term."
                )
                logging.info(f"Built prompt with {len(context_docs)} context documents")

            logging.info("Sending request to Gemini model...")
            response = current_app.gemini_model.predict(prompt)
            ai_text = response.text
            logging.info("Received response from Gemini model")

            # Update chat history
            new_messages = [
                {'role': 'user', 'content': user_message, 'timestamp': datetime.utcnow().isoformat()},
                {'role': 'assistant', 'content': ai_text, 'timestamp': datetime.utcnow().isoformat()}
            ]
            
            # Keep only the last 10 messages to avoid storing too much history
            updated_messages = (messages + new_messages)[-10:]
            save_chat_history(current_user.id, updated_messages)

            return jsonify({
                'success': True,
                'response': ai_text,
                'context_used': bool(context_docs)
            })

        except Exception as e:
            logging.error(f"Error processing chat request: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': 'An error occurred while processing your request',
                'details': str(e)
            }), 500

    except Exception as e:
        logging.error(f"Unexpected error in chat_api: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred',
            'details': str(e)
        }), 500

