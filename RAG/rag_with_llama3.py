from dotenv import load_dotenv
import os

from langchain_groq import ChatGroq
from langchain.chains import ConversationalRetrievalChain

load_dotenv()

# groq_api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(temperature=0, model_name="llama3-8b-8192")
# chain = ConversationalRetrievalChain.from_llm(llm,
#                                               vectorstore.as_retriever(),
#                                               return_source_documents=True)
# result = chain({"question": "What’s new with Llama 3?", "chat_history": []})
# md(result['answer'])
