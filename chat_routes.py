from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from google.cloud import firestore
import google.generativeai as genai
import os
from datetime import datetime

# Create blueprint
chat_bp = Blueprint('chat', __name__)

# Initialize Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

# Initialize Firestore
db = firestore.Client(project=os.getenv('GOOGLE_CLOUD_PROJECT'))

def get_chat_history(user_id):
    """Retrieve chat history for a user"""
    try:
        chat_doc = db.collection('chats').document(user_id).get()
        if chat_doc.exists:
            return chat_doc.to_dict().get('messages', [])
        return []
    except Exception as e:
        print(f"Error getting chat history: {e}")
        return []

def save_chat_history(user_id, messages):
    """Save chat history for a user"""
    try:
        chat_ref = db.collection('chats').document(user_id)
        chat_ref.set({
            'user_id': user_id,
            'messages': messages[-10:],  # Keep only last 10 messages
            'updated_at': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error saving chat history: {e}")

def get_restaurant_recommendations(query):
    """Generate restaurant recommendations using Gemini"""
    try:
        # This is a placeholder - in a real app, you would:
        # 1. Generate embeddings for the query
        # 2. Search similar vectors in MongoDB Atlas
        # 3. Return relevant restaurant data
        
        # For now, we'll just use Gemini to generate a response
        response = model.generate_content(
            f"Generate a restaurant recommendation based on: {query}"
        )
        
        return {
            'success': True,
            'response': response.text,
            'restaurants': []  # This would contain actual restaurant data
        }
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@chat_bp.route('/chat')
@login_required
def chat():
    """Render the chat interface"""
    return render_template('chat.html', 
                         username=current_user.email.split('@')[0])

@chat_bp.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Get chat history
        messages = get_chat_history(current_user.id)
        
        # Add user message to history
        messages.append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Get recommendations
        response = get_restaurant_recommendations(user_message)
        
        # Add assistant response to history
        if response['success']:
            messages.append({
                'role': 'assistant',
                'content': response['response'],
                'restaurants': response.get('restaurants', []),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Save updated chat history
            save_chat_history(current_user.id, messages)
            
            return jsonify({
                'success': True,
                'response': response['response'],
                'restaurants': response.get('restaurants', [])
            })
        else:
            return jsonify({
                'success': False,
                'error': response.get('error', 'Failed to get recommendations')
            }), 500
            
    except Exception as e:
        print(f"Error in chat API: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your request'
        }), 500
