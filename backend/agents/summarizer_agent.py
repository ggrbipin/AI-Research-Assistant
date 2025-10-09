"""
Summarizer Agent: Summarizes retrieved chunks into a coherent answer
"""
import os
from openai import OpenAI
from utils.logger import agent_logger


class SummarizerAgent:
    def __init__(self):
        self.name = "Summarizer Agent"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        agent_logger.info(f"{self.name} initialized")

    def summarize(self, query: str, chunks: list[str], conversation_context: str = ""):
        """
        Summarize retrieved chunks into a coherent answer

        Args:
            query: Original user question
            chunks: List of relevant text chunks from FAISS
            conversation_context: Previous conversation history for follow-up queries

        Returns:
            dict with summary and metadata
        """
        agent_logger.info(f"{self.name}: Starting summarization for query='{query}'")
        agent_logger.debug(f"{self.name}: Processing {len(chunks)} chunks")

        if not chunks:
            agent_logger.warning(f"{self.name}: No chunks provided for summarization")
            return {
                "status": "error",
                "message": "No chunks to summarize",
                "summary": ""
            }

        # Combine chunks into context
        context = "\n\n---\n\n".join(chunks)

        # Add conversation context if available
        conversation_prefix = ""
        if conversation_context:
            conversation_prefix = f"{conversation_context}\n\n"

        prompt = f"""{conversation_prefix}You are a document-based Q&A assistant. Answer ONLY using information explicitly found in the provided context.

NOTE: If this is a follow-up question (like "What about...", "Can you explain more...", "Tell me about that..."), use the conversation history above to understand what the user is referring to.

Context from documents:
{context}

User's Question: {query}

CRITICAL RULES - READ CAREFULLY:
1. Answer ONLY using information explicitly stated in the context above
2. DO NOT add information from your general knowledge
3. DO NOT make assumptions or inferences beyond what's written
4. If the exact answer is in the context, use it word-for-word or paraphrase it closely
5. If information is NOT in the context, say "This information is not found in the document."

RESPONSE LENGTH:
SIMPLE QUESTIONS (what is, how much, when, who):
- 1-2 sentences maximum
- State the fact from the context directly
- Example: "What is expected outcome?" + Context has "Expected: X" → Answer: "X"

COMPLEX QUESTIONS (summarize, explain, describe in detail):
- Provide detailed answer but ONLY using context information
- Do not add external examples or explanations

WARNING: If you add information not in the context, the answer is WRONG.

Your answer (strictly from context only):"""

        try:
            model = os.getenv("LLM_MODEL", "gpt-4")
            agent_logger.info(f"{self.name}: 🤖 Invoking LLM - Model: {model}, Temperature: 0.2")

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful research and document extraction assistant. You must provide accurate, well-structured answers based only on the context provided by the user. You MUST answer using ONLY the information in the context and never use your general knowledge. If the answer is not in the context, respond with: 'Information not found in document."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2  # Lower temperature for more focused summaries
            )

            summary = response.choices[0].message.content

            # Log token usage
            usage = response.usage
            agent_logger.info(
                f"{self.name}: ✅ LLM Response received | "
                f"Tokens: {usage.prompt_tokens} input + {usage.completion_tokens} output = {usage.total_tokens} total | "
                f"Response length: {len(summary)} chars"
            )

            return {
                "status": "success",
                "summary": summary,
                "num_chunks_used": len(chunks)
            }

        except Exception as e:
            agent_logger.error(f"{self.name}: Error during summarization: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error during summarization: {str(e)}",
                "summary": ""
            }
