from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
import os

load_dotenv()
"""
llm = ChatGroq(
   model="openai/gpt-oss-120b",
   temperature = 0,
)
"""

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0,
)

llm2 = ChatOllama(
    model="ministral-3:3b",
    base_url="http://localhost:11434",
    temperature=0,
    num_ctx=32768,
)