# query_only.py

# 1. Basic Imports and Configuration
import nest_asyncio
import sys

from llama_index.core import Settings, StorageContext, PromptTemplate
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import KnowledgeGraphRAGRetriever
from llama_index.graph_stores.neo4j import Neo4jGraphStore
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding

from config import config
from prompt_templates.cot_prompt_template import COT_PROMPT_TEMPLATE

nest_asyncio.apply()

# 2. Initialize Ollama LLM and Embedding Model
llm = Ollama(
    model=config.OLLAMA_LLM_MODEL,
    base_url=f"http://{config.OLLAMA_HOST}:{config.OLLAMA_PORT}",
    request_timeout=600.0,
)
Settings.llm = llm

embed_model = OllamaEmbedding(
    model_name=config.OLLAMA_EMBED_MODEL,
    base_url=f"http://{config.OLLAMA_HOST}:{config.OLLAMA_PORT}",
)
Settings.embed_model = embed_model

# 3. Connect to Existing Neo4j Knowledge Graph
graph_store = Neo4jGraphStore(
    username=config.NEO4J_USERNAME,
    password=config.NEO4J_PASSWORD,
    url=config.NEO4J_URI,
    database="neo4j",
    timeout=600.0,
)

storage_context = StorageContext.from_defaults(graph_store=graph_store)

# 4. Set Up Retriever and Query Engine
graph_rag_retriever = KnowledgeGraphRAGRetriever(
    storage_context=storage_context,
    verbose=True,
)

query_engine = RetrieverQueryEngine.from_args(
    graph_rag_retriever,
    embed_model=embed_model,
)

# 5. Apply Prompt Template (Chain-of-Thought Style)
query_engine.update_prompts(
    {"response_synthesizer:text_qa_template": COT_PROMPT_TEMPLATE}
)

# 6. Start an Interactive Question-Answer Loop
print("Neo4j RAG assistant is ready. Ask a question or press Enter to exit.\n")

try:
    while True:
        user_query = input("Question: ")
        if not user_query.strip():
            print("Exiting.")
            break

        answer = query_engine.query(user_query)
        print("\nAnswer:\n" + str(answer) + "\n")

except (KeyboardInterrupt, EOFError):
    print("\nExiting.")
    sys.exit(0)
