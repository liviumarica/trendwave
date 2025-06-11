import os
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
import google.generativeai as genai
from config import settings

class VectorStore:
    def __init__(self):
        """Initialize MongoDB connection and Gemini AI."""
        self.client = MongoClient(settings.MONGODB_URI)
        self.db = self.client[settings.DB_NAME]
        self.collection: Collection = self.db[settings.COLLECTION_NAME]
        
        # Initialize Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for the given text using Gemini."""
        try:
            # Generate embedding using Gemini
            response = self.model.embed_content(
                content=text,
                task_type="retrieval_document"
            )
            return response['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise
    
    def vector_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar restaurants using vector search."""
        try:
            # Generate embedding for the query
            query_embedding = self.get_embedding(query)
            
            # Vector search pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": settings.VECTOR_INDEX,
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": 50,
                        "limit": limit,
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "name": 1,
                        "cuisine": 1,
                        "address": 1,
                        "rating": 1,
                        "price_range": 1,
                        "description": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            return results
            
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []
    
    def generate_recommendation(self, query: str, search_results: List[Dict]) -> str:
        """Generate a natural language recommendation using Gemini."""
        try:
            # Format search results for the prompt
            results_str = "\n".join([
                f"- {r['name']} ({r['cuisine']}): {r.get('description', 'No description')} "
                f"Rating: {r.get('rating', 'N/A')}, Price: {r.get('price_range', 'N/A')}"
                for r in search_results
            ])
            
            prompt = f"""
            Based on the following restaurant search results, provide a personalized recommendation:
            
            User query: {query}
            
            Search results:
            {results_str}
            
            Please provide a friendly, natural response that:
            1. Acknowledges the user's preferences
            2. Recommends 1-3 restaurants with reasons why they're a good match
            3. Includes key details like cuisine, price range, and rating
            4. Is concise and engaging
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"Error generating recommendation: {e}")
            return "I'm sorry, I couldn't generate a recommendation at the moment. Please try again later."
    
    def get_recommendations(self, query: str, limit: int = 3) -> Dict[str, Any]:
        """Get restaurant recommendations based on natural language query."""
        try:
            # First, perform vector search
            search_results = self.vector_search(query, limit=limit)
            
            if not search_results:
                return {
                    "success": False,
                    "message": "No restaurants found matching your criteria.",
                    "results": []
                }
            
            # Generate natural language recommendation
            recommendation = self.generate_recommendation(query, search_results)
            
            return {
                "success": True,
                "recommendation": recommendation,
                "results": search_results
            }
            
        except Exception as e:
            print(f"Error in get_recommendations: {e}")
            return {
                "success": False,
                "message": "An error occurred while processing your request.",
                "results": []
            }
