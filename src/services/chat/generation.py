from openai import OpenAI
from typing import List, Dict
from backend.services.chat.validation import ConstitutionValidationService
from backend.models.response import ChatbotResponse
from backend.utils.logging import logger
from datetime import datetime


class ChatService:
    def __init__(self, validation_service: ConstitutionValidationService = None):
        self.validation_service = validation_service or ConstitutionValidationService()
        self.openai_client = OpenAI()
        
    def generate_response(self, question: str, context: List[Dict] = None) -> ChatbotResponse:
        """
        Generate a response to the user's question based on the retrieved context
        """
        # If no context provided or context is empty, return the unavailable topic response
        if not context or len(context) == 0:
            response_text = self.validation_service.handle_unavailable_topic()
            confidence = "NONE"
            sources = []
        else:
            # Prepare the context for the LLM
            context_texts = [item['text'] for item in context]
            context_str = "

".join(context_texts)
            
            # Create the prompt for the LLM
            prompt = f"""Answer the following question based only on the provided context from the textbook. 
            If the answer is not in the context, respond with: This topic is not covered in the book yet.
            
            Context: {context_str}
            
            Question: {question}
            
            Answer:"""
            
            try:
                # Generate response using OpenAI
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=0.3
                )
                
                response_text = response.choices[0].message.content
                
                # Validate the response against constitution rules
                if not self.validation_service.validate_response(response_text, context_texts):
                    response_text = self.validation_service.handle_unavailable_topic()
                    
                # Determine confidence based on context availability
                confidence = "HIGH" if context else "NONE"
                sources = [item['source'] for item in context if 'source' in item]
                
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                response_text = self.validation_service.handle_unavailable_topic()
                confidence = "NONE"
                sources = []
        
        # Create and return the response object with proper timestamp
        response_obj = ChatbotResponse(
            id="response_" + str(hash(question))[:8],
            content=response_text,
            questionId="question_" + str(hash(question))[:8],
            timestamp=datetime.now(),
            confidence=confidence,
            sources=sources
        )
        
        return response_obj
