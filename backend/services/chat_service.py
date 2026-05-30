"""
Chat service using Google Gemini API for RAG-based answer generation.

Takes retrieved context chunks and a user query, builds a structured
prompt, and generates an answer grounded in the provided context.
"""

import google.generativeai as genai
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """Generate answers using retrieved context and Gemini API"""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        """
        Initialize the Gemini chat service.

        Args:
            api_key: Google Gemini API key
            model_name: Gemini model to use
        """
        self.api_key = api_key
        self.model_name = model_name
        self._model = None

        if api_key and api_key != "your_gemini_api_key_here":
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(model_name)
            logger.info(f"ChatService initialized with model: {model_name}")
        else:
            logger.warning("ChatService: No valid Gemini API key — chat will not work")

    def generate_answer(self, query: str, context_chunks: List[Dict]) -> str:
        """
        Generate an answer based on retrieved context chunks.

        Args:
            query: User's question
            context_chunks: List of relevant chunks with text and metadata

        Returns:
            Generated answer string

        Raises:
            ValueError: If Gemini API key is not configured
            RuntimeError: If Gemini API call fails
        """
        if not self._model:
            raise ValueError(
                "Gemini API key is not configured. "
                "Please set GEMINI_API_KEY in your backend/.env file. "
                "Get a key at https://aistudio.google.com/apikey"
            )

        if not context_chunks:
            return (
                "I couldn't find any relevant information in the uploaded documents "
                "to answer your question. Please try rephrasing or upload more relevant documents."
            )

        # Build structured context from retrieved chunks
        context_parts = []
        for i, chunk in enumerate(context_chunks):
            header = f"[Source {i + 1}]"
            if chunk.get("document_name"):
                header += f" Document: {chunk['document_name']}"
            if chunk.get("page_number"):
                header += f" | Page {chunk['page_number']}"

            context_parts.append(f"{header}\n{chunk['text']}")

        context = "\n\n---\n\n".join(context_parts)

        prompt = f"""You are a helpful research assistant. Answer the user's question based ONLY on the provided context from their uploaded documents.

CONTEXT FROM DOCUMENTS:
{context}

USER QUESTION: {query}

INSTRUCTIONS:
- Answer based ONLY on the provided context — do not use external knowledge
- Be accurate, concise, and helpful
- Reference specific sources (e.g., "According to Source 1...") when relevant
- If the context doesn't contain enough information, clearly state what's missing
- Use clear formatting with paragraphs and bullet points where appropriate
- Do not fabricate or assume information not present in the context"""

        try:
            response = self._model.generate_content(prompt)
            answer = response.text
            logger.info(f"Generated answer ({len(answer)} chars) for: {query[:60]}...")
            return answer

        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise RuntimeError(f"Failed to generate answer: {str(e)}")
