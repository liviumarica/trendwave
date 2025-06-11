from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
from extensions import db
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

@chat_bp.route('/chat')
@login_required
def chat():
    """Render the chat interface"""
    return render_template('chat.html', username=current_user.email.split('@')[0])

@chat_bp.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """Handle chat messages and return AI responses"""
    try:
        logging.info("--- chat_api: Entered function ---")
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
            
        # Format existing messages for Gemini API history
        api_call_history = []
        if messages: # Ensure messages is not empty
            api_call_history = [
                {'role': msg['role'], 'parts': [msg['content']]} 
                for msg in messages
            ]
        
        # Start chat with previous history and send the new user message
        logging.info(f"--- chat_api: About to call Gemini. User message: '{user_message}'. History length: {len(api_call_history)} ---")
        chat = gemini_model.start_chat(history=api_call_history)
        response = chat.send_message(user_message)
        
        # Add current user message to messages list for saving
        messages.append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Add assistant response to messages list for saving
        messages.append({
            'role': 'assistant',
            'content': response.text,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Save updated chat history (including new user message and AI response)
        save_chat_history(current_user.id, messages)
        
        return jsonify({
            'success': True,
            'response': response.text,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logging.exception("An error occurred in the chat API:")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your request'
        }), 500
