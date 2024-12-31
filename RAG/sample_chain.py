# import bs4
# from langchain import hub
# from langchain_community.document_loaders import WebBaseLoader
# from langchain_community.vectorstores import Chroma
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.runnables import RunnablePassthrough
# from langchain_openai import OpenAIEmbeddings
# from langchain_text_splitters import RecursiveCharacterTextSplitter

def format_docs():
    pass

retriever = "Hiiii"
question = "Nooooo"
prompt = """
You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.
Question: {question} 
Context: {context} 
Answer:
"""
llm = "Gemini"

print(prompt)

rag_chain = (
    {"context": retriever | format_docs, "question": question}
    | prompt
    | llm
    # | StrOutputParser()
)
print(rag_chain)