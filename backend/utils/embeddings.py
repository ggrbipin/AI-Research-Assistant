import os
from openai import OpenAI
from utils.logger import api_logger

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text: str, model="text-embedding-3-small"):
    """
    Get embedding vector for text using OpenAI
    """
    api_logger.debug(f"🔢 Generating embedding - Model: {model}, Text length: {len(text)} chars")

    response = client.embeddings.create(
        input=text,
        model=model
    )

    # Log token usage
    usage = response.usage
    api_logger.debug(f"✅ Embedding generated | Tokens: {usage.total_tokens}")

    return response.data[0].embedding

def call_openai(prompt: str, model: str = None):
    """
    Generic OpenAI API call wrapper for agents
    """
    if model is None:
        model = os.getenv("LLM_MODEL", "gpt-4")

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
