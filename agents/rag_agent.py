from typing import Dict, List, Any, Optional
import logging
import os
import asyncio
from pydantic import BaseModel
import openai

from vector_store.retriever import QdrantRetriever
from utils.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

class RAGAgent:
    """
    RAG Agent that uses multiple LLM providers to process queries with retrieved context.
    """

    def __init__(self):
        """Initialize the RAG Agent with required services."""
        # Initialize Google AI if available
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            logger.warning("GOOGLE_API_KEY environment variable is not set.")
            self.genai_client = None
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=google_api_key)
                self.genai_client = genai
                # Initialize the generative model
                self.model = genai.GenerativeModel('gemini-pro')  # or gemini-1.5-pro for newer models
            except ImportError:
                logger.error("google-generativeai package not installed")
                self.genai_client = None
            except Exception as e:
                logger.error(f"Failed to initialize Google Generative AI: {str(e)}")
                self.genai_client = None

        # Initialize OpenRouter client if available
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
        if not openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY environment variable is not set.")
            self.openrouter_client = None
        else:
            try:
                self.openrouter_client = openai.AsyncOpenAI(
                    api_key=openrouter_api_key,
                    base_url=base_url
                )
                self.openrouter_model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1-0528:free")
            except Exception as e:
                logger.error(f"Failed to initialize OpenRouter client: {str(e)}")
                self.openrouter_client = None

        # Initialize Cohere as fallback if available
        cohere_api_key = os.getenv("COHERE_API_KEY")
        if not cohere_api_key:
            logger.warning("COHERE_API_KEY environment variable is not set.")
            self.cohere_client = None
        else:
            try:
                import cohere
                self.cohere_client = cohere.Client(api_key=cohere_api_key)
            except ImportError:
                logger.error("cohere package not installed")
                self.cohere_client = None
            except Exception as e:
                logger.error(f"Failed to initialize Cohere client: {str(e)}")
                self.cohere_client = None

        self.qdrant_retriever = QdrantRetriever()
        self.embedding_service = EmbeddingService()


    def _clean_response(self, response: str) -> str:
        """
        Clean up the response to remove markdown formatting and organize it better.
        """
        import re

        # Remove ALL markdown formatting - brute force approach
        cleaned = response

        # Multiple passes to ensure all markdown is removed
        for _ in range(3):
            # Remove bold markdown (**text** and __text__)
            cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
            cleaned = re.sub(r'__([^_]+)__', r'\1', cleaned)
            # Remove italic markdown (*text* and _text_)
            cleaned = re.sub(r'\*([^\*]+)\*', r'\1', cleaned)
            cleaned = re.sub(r'_([^\_]+)_', r'\1', cleaned)

        # Final pass - remove any remaining markdown characters
        cleaned = cleaned.replace('**', '').replace('__', '').replace('*', '').replace('_', '')

        # Remove markdown headings
        cleaned = re.sub(r'^#{1,6}\s*', '', cleaned, flags=re.MULTILINE)

        # Replace markdown lists with bullet points
        cleaned = re.sub(r'\n\d+\.\s+', r'\n• ', cleaned)  # Ordered lists to bullet points
        cleaned = re.sub(r'\n[-+]\s+', r'\n• ', cleaned)  # Unordered lists

        # Clean up whitespace
        cleaned = re.sub(r'\n\s*\n', r'\n\n', cleaned)  # Normalize paragraph breaks
        cleaned = re.sub(r'  +', ' ', cleaned)  # Normalize spaces
        cleaned = cleaned.strip()

        # Limit length for conciseness
        lines = cleaned.split('\n')
        if len(lines) > 10:
            cleaned = '\n'.join(lines[:10])

        return cleaned


    def _format_sources(self, sources: List[Dict]) -> List[Dict]:
        """
        Format sources to be more organized and readable.
        """
        formatted_sources = []
        for i, source in enumerate(sources):
            # Create a more readable source description
            formatted_source = {
                'id': source.get('id', ''),
                'source': source.get('source', ''),
                'score': source.get('score', 0),
                'page_content': source.get('page_content', '')[:200],  # Keep truncation
                'reference': f"Source {i+1}"  # Add a more organized reference
            }
            formatted_sources.append(formatted_source)
        return formatted_sources


    async def process_query(
        self,
        query: str,
        user_selected_text: Optional[str] = None,
        top_k: int = 5,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Process a user query using RAG methodology.

        Args:
            query: The user's question
            user_selected_text: Optional text selected by user from the website
            top_k: Number of context chunks to retrieve
            max_tokens: Maximum tokens in the response
            temperature: Temperature for response generation

        Returns:
            Dictionary containing response, sources, and context
        """
        try:
            logger.info(f"Processing query: {query[:100]}...")

            # Retrieve relevant context from vector store with specified top_k
            retrieved_context = await self.qdrant_retriever.search(query, top_k=5)  # Fixed to 5 as per requirements

            # Combine query context with user-selected text if provided
            combined_context = ""
            sources = []

            if user_selected_text:
                combined_context += f"User-selected text: {user_selected_text}\n\n"

            for idx, doc in enumerate(retrieved_context):
                combined_context += f"[Source {idx+1}]: {doc['content']}\n\n"
                sources.append({
                    'id': doc.get('id', ''),
                    'source': doc.get('metadata', {}).get('source', ''),
                    'score': doc.get('score', 0),
                    'page_content': doc.get('content', '')[:200]  # Truncate for brevity
                })

            # Create a prompt for the LLM with strict rules
            llm_prompt = f"""You are an expert assistant for the Physical AI & Humanoid Robotics textbook. Answer the user's question based ONLY on the following context from the book:

            CONTEXT:
            {combined_context}

            USER QUESTION: {query}

            STRICT RULES:
            1. Answer ONLY from the provided book context
            2. Do NOT use general knowledge
            3. Do NOT hallucinate
            4. If the answer is not found in the book, reply EXACTLY: "This information is not available in the book."
            5. Keep answers short and book-accurate (aim for 2-3 paragraphs maximum)
            6. Reference specific parts of the book context when possible
            7. Maintain a professional academic tone
            8. DO NOT use any markdown formatting like **, *, __, #, etc. - return plain text only
            9. Organize information with clear structure and logical flow

            ANSWER:"""

            # Try different LLM providers in order of preference
            assistant_response = None

            # First, try OpenRouter if available
            if self.openrouter_client:
                try:
                    response = await self.openrouter_client.chat.completions.create(
                        model=self.openrouter_model,
                        messages=[
                            {"role": "system", "content": "You are an expert assistant for the Humanoid Robotics AI textbook. Answer questions based on the provided context."},
                            {"role": "user", "content": llm_prompt}
                        ],
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    assistant_response = response.choices[0].message.content
                    logger.info("Successfully generated response using OpenRouter")
                except Exception as e:
                    logger.error(f"Error with OpenRouter: {str(e)}")

            # If OpenRouter fails or is not available, try Google AI
            if not assistant_response and self.genai_client:
                try:
                    response = self.model.generate_content(
                        llm_prompt,
                        generation_config=self.genai_client.types.GenerationConfig(
                            max_output_tokens=max_tokens,
                            temperature=temperature
                        )
                    )
                    assistant_response = response.text
                    logger.info("Successfully generated response using Google AI")
                except Exception as e:
                    logger.error(f"Error with Google Generative AI: {str(e)}")

            # If both fail, try Cohere as final fallback
            if not assistant_response and self.cohere_client:
                try:
                    response = self.cohere_client.chat(
                        message=llm_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    assistant_response = response.text
                    logger.info("Successfully generated response using Cohere")
                except Exception as e:
                    logger.error(f"Error with Cohere: {str(e)}")

            # If all LLM providers fail, return an error response
            if not assistant_response:
                if not retrieved_context:
                    assistant_response = "No relevant information found in the textbook, and no LLM provider is available to generate a response. Please check that at least one of the following is properly configured: OPENROUTER_API_KEY, GOOGLE_API_KEY, or COHERE_API_KEY, and that the vector database is accessible."
                else:
                    assistant_response = "No LLM provider is available to generate a response. Please check that at least one of the following is properly configured: OPENROUTER_API_KEY, GOOGLE_API_KEY, or COHERE_API_KEY."

            # Clean up the response to remove markdown formatting and make it concise
            cleaned_response = self._clean_response(assistant_response)

            # Format sources to be more organized
            formatted_sources = self._format_sources(sources)

            result = {
                "response": cleaned_response,
                "sources": formatted_sources,
                "context": combined_context,
                "query": query
            }

            logger.info(f"Successfully processed query. Retrieved {len(sources)} sources.")
            return result

        except Exception as e:
            logger.error(f"Error processing query '{query[:50]}...': {str(e)}")
            raise

    def is_healthy(self) -> bool:
        """
        Check if the RAG agent is healthy and can process queries.
        """
        try:
            # Check if at least one LLM provider is available
            health_status = False

            # Test Google AI if available
            if self.genai_client:
                try:
                    test_response = self.model.generate_content("Hello, are you working?")
                    health_status = True
                except Exception as e:
                    logger.warning(f"Google AI health check failed: {str(e)}")

            # Test Cohere if Google AI failed
            if not health_status and self.cohere_client:
                try:
                    import cohere
                    cohere_client = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))
                    cohere_client.models.list()
                    health_status = True
                except Exception as e:
                    logger.warning(f"Cohere health check failed: {str(e)}")

            # Even if no LLM provider is healthy, we can still consider the agent healthy if Qdrant is accessible
            # since the core functionality is to retrieve information from the vector store
            qdrant_healthy = self.qdrant_retriever.is_healthy()

            return health_status or qdrant_healthy
        except Exception as e:
            logger.error(f"RAG agent health check failed: {str(e)}")
            return False

    def cleanup(self):
        """
        Cleanup resources used by the RAG agent.
        """
        try:
            # Delete the assistant if it's no longer needed
            if hasattr(self, 'assistant') and self.assistant:
                self.openai_client.beta.assistants.delete(self.assistant.id)
        except Exception as e:
            logger.warning(f"Failed to cleanup RAG agent resources: {str(e)}")