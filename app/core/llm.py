from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_ollama import ChatOllama

load_dotenv()

#llm = ChatGroq(
#   model="openai/gpt-oss-120b",
#)

llm = ChatOllama(
    model="ministral-3:3b",
    base_url="http://localhost:11434",
    temperature=0,
    num_ctx=32768,
)