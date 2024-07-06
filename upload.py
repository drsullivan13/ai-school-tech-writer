from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import WebBaseLoader
import bs4

load_dotenv()

os.environ["PINECONE_API_KEY"] = os.getenv("PINECONE_API_KEY")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

loader = WebBaseLoader(
    web_paths=("https://github.com/banesullivan/README/blob/main/README.md/", "https://github.com/mhucka/readmine/blob/main/README.md"),
    bs_kwargs=dict(
        parse_only=bs4.SoupStrainer(
            class_=("markdown-body entry-content container-lg")
        )
    ),
)

docs = loader.load()

# Split documents into smaller chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
documents = text_splitter.split_documents(docs)
print(f"Going to add {len(documents)} to Pinecone")

# Choose the embedding model and vector store 
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
PineconeVectorStore.from_documents(documents=documents, embedding=embeddings, index_name=PINECONE_INDEX)
print("Loading to vectorstore done")