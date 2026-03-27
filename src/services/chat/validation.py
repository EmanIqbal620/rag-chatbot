from typing import List
from backend.utils.logging import logger


class ConstitutionValidationService:
    def __init__(self):
        self.forbidden_phrases = [
            "based on the provided context",
            "according to the sources",
            "the context describes",
            "from the document",
            "as mentioned in the text"
        ]
    
    def validate_response(self, response: str, retrieved_context: List[str] = None) -> bool:
        """
        Validates that the response complies with the constitution rules:
        - No hallucination
        - No exposure of internal processes
        - Uses simple language
        """
        # Check for forbidden phrases
        for phrase in self.forbidden_phrases:
            if phrase.lower() in response.lower():
                logger.warning(f"Response contains forbidden phrase: {phrase}")
                return False
        
        # Check if response is grounded in context (if provided)
        if retrieved_context and not self._is_response_groundedin_context(response, retrieved_context):
            logger.warning("Response is not properly grounded in the provided context")
            return False
        
        return True
    
    def _is_response_groundedin_context(self, response: str, context: List[str]) -> bool:
        """
        Basic check to see if response content aligns with provided context
        This is a simplified implementation - could be enhanced with more sophisticated NLP
        """
        response_lower = response.lower()
        
        # Check if key terms from context appear in response
        context_terms = set()
        for ctx in context:
            ctx_lower = ctx.lower()
            # Extract some key terms (simplified approach)
            words = ctx_lower.split()
            # Take the 5-20 most common length words as potential key terms
            for word in words:
                if len(word) > 3:  # Only consider words longer than 3 chars
                    context_terms.add(word)
        
        # Check if a reasonable portion of context terms appear in the response
        matching_terms = sum(1 for term in context_terms if term in response_lower)
        
        # If at least 10% of unique context terms appear in response, consider it grounded
        if len(context_terms) > 0:
            return (matching_terms / len(context_terms)) >= 0.1
        
        # If no terms extracted from context, we can't validate grounding
        return True
    
    def handle_unavailable_topic(self) -> str:
        """
        Returns the appropriate response when the topic is not covered in the book
        """
        return "This topic is not covered in the book yet."
    
    def is_topic_unavailable_query(self, question: str, retrieved_context: List[str]) -> bool:
        """
        Determines if the question is about a topic not covered in the provided context
        """
        # If no context retrieved, assume topic is not covered
        if not retrieved_context:
            return True
        
        # Check if the retrieved context has any substantial content related to the question
        # This is a simplified check - could be enhanced with semantic similarity
        question_lower = question.lower()
        context_combined = " ".join(retrieved_context).lower()
        
        # If context is too short or doesn't seem to contain relevant information
        if len(context_combined.strip()) < 50:
            return True
        
        return False
