# 1. Basic Setup and Imports
import nest_asyncio
import logging
import pathlib

from llama_index.core import (
    SummaryIndex,
    Document,
    KnowledgeGraphIndex,
    VectorStoreIndex,
    Settings,
    SimpleDirectoryReader,
    PromptTemplate,
    StorageContext,
    ServiceContext,
)

from llama_index.core.tools import QueryEngineTool
from llama_index.graph_stores.neo4j import Neo4jGraphStore
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding

from config import config
from helper.util_doc_helper import build_docs_with_metadata
from helper.util_image_helper import extract_images_from_pdf, describe_image_with_llava
from helper.util_link_helper import (
    extract_links_from_directory,
    push_links_to_graph,
    update_link_status,
    fetch_public_docs,
    preprocess_downloaded_docs,
    add_main_pdfs_to_neo4j,
)
from prompt_templates.cot_prompt_template import COT_PROMPT_TEMPLATE

# Logging and asyncio patch
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
nest_asyncio.apply()

# 2. Model Configuration: LLM and Embedding
llm = Ollama(
    model=config.OLLAMA_LLM_MODEL,
    base_url=f"http://{config.OLLAMA_HOST}:{config.OLLAMA_PORT}",
    request_timeout=600.0
)
Settings.llm = llm

embed_model = OllamaEmbedding(
    model_name=config.OLLAMA_EMBED_MODEL,
    base_url=f"http://{config.OLLAMA_HOST}:{config.OLLAMA_PORT}",
    trust_remote_code=True,
)
Settings.embed_model = embed_model

# 3. Load PDF Documents from Directory
docs = []
for pdf_path in pathlib.Path(config.DOC_DIR).glob("*.pdf"):
    docs.extend(build_docs_with_metadata(str(pdf_path)))

# 4. Steps for Neo4j Graph Initialization from PDF Links
link_map = extract_links_from_directory(config.DOC_DIR)

add_main_pdfs_to_neo4j(
    uri=config.NEO4J_URI,
    user=config.NEO4J_USERNAME,
    pwd=config.NEO4J_PASSWORD,
    docs_dir=config.DOC_DIR
)

push_links_to_graph(
    uri=config.NEO4J_URI,
    user=config.NEO4J_USERNAME,
    pwd=config.NEO4J_PASSWORD,
    link_map=link_map
)

update_link_status(
    uri=config.NEO4J_URI,
    user=config.NEO4J_USERNAME,
    pwd=config.NEO4J_PASSWORD
)

# 5. Process Linked External Documents (e.g. public URLs in PDFs)
RAW_DIR = pathlib.Path(config.DOWNLOAD_DOC_DIR) / "linked_raw"
CLEAN_DIR = pathlib.Path(config.DOWNLOAD_DOC_DIR) / "linked_clean"

fetch_public_docs(
    uri=config.NEO4J_URI,
    user=config.NEO4J_USERNAME,
    pwd=config.NEO4J_PASSWORD,
    raw_dir=RAW_DIR
)

preprocess_downloaded_docs(RAW_DIR, CLEAN_DIR)

extra_docs = []

if CLEAN_DIR.exists() and any(CLEAN_DIR.iterdir()):
    for file in CLEAN_DIR.iterdir():
        if file.suffix.lower() == ".pdf":
            extra_docs.extend(build_docs_with_metadata(str(file)))
        elif file.suffix.lower() == ".txt":
            text = file.read_text(encoding="utf-8")
            extra_docs.append(Document(
                text=text,
                metadata={
                    "source": "linked_doc",
                    "filename": file.name,
                    "type": "text"
                }
            ))
    docs.extend(extra_docs)
else:
    logger.warning(f"No files found in {CLEAN_DIR}. Skipping extra_docs loading.")

# # 6. Output Discovered Links
# for doc_name, links in link_map.items():
#     print(f"\nLinks found in {doc_name}:")
#     for link in links:
#         print(f" - Page {link['page']}: {link['uri']}")

# 7. Extract Images from PDFs and Generate Descriptions
IMG_DIR = pathlib.Path("output-images")
image_caption_docs = []

for pdf_file in pathlib.Path(config.DOC_DIR).glob("*.pdf"):
    image_paths = extract_images_from_pdf(str(pdf_file), IMG_DIR)

    for img_path, page_number in image_paths:
        caption = describe_image_with_llava(img_path)
        print(f"\n[Image]: {img_path.name}\n[Description]: {caption}")

        doc = Document(
            text=caption,
            metadata={
                "source": "image",
                "filename": str(img_path.name),
                "pdf_name": pdf_file.name,
                "page": page_number
            }
        )
        image_caption_docs.append(doc)

docs.extend(image_caption_docs)

# 8. Build Knowledge Graph Index in Neo4j
graph_store = Neo4jGraphStore(
    username=config.NEO4J_USERNAME,
    password=config.NEO4J_PASSWORD,
    url=config.NEO4J_URI,
    database="neo4j",
    timeout=600.0
)

storage_context = StorageContext.from_defaults(graph_store=graph_store)

kg_index = KnowledgeGraphIndex.from_documents(
    docs,
    storage_context=storage_context,
    max_triplets_per_chunk=8,
    embed_model=embed_model,
    show_progress=True
)

# 9. Configure Query Engine using KG Retriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import KnowledgeGraphRAGRetriever

graph_rag_retriever = KnowledgeGraphRAGRetriever(
    storage_context=storage_context,
    verbose=True
)

query_engine = RetrieverQueryEngine.from_args(
    graph_rag_retriever,
    embed_model=embed_model
)

query_engine.update_prompts(
    {"response_synthesizer:text_qa_template": COT_PROMPT_TEMPLATE}
)

# 10. Run Interactive Query Loop
while user_query := input("\n\nWhat do you want to know about these files?\n"):
    response = query_engine.query(user_query)
    print(str(response))
