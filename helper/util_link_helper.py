import os, pathlib, requests, fitz
import urllib

from bs4 import BeautifulSoup
from neo4j import GraphDatabase


# 1. link extraction
def extract_links_from_pdf(pdf_path: str) -> list[dict]:
    """Return [{'page': int, 'uri': str}, …] for one PDF."""
    doc = fitz.open(pdf_path)
    links = []
    for pnum, page in enumerate(doc):
        for l in page.get_links():
            if "uri" in l:
                links.append({"page": pnum + 1, "uri": l["uri"]})
    return links


def extract_links_from_directory(pdf_dir: str) -> dict[str, list[dict]]:
    """Return {filename: [link_dict, …], …} for every *.pdf in pdf_dir."""
    link_map = {}
    for fn in os.listdir(pdf_dir):
        if fn.lower().endswith(".pdf"):
            link_map[fn] = extract_links_from_pdf(os.path.join(pdf_dir, fn))
    return link_map


# 2. push PDF→link into neo4j
def push_links_to_graph(uri, user, pwd, link_map):
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    with driver.session(database="neo4j") as s:
        for pdf_name, links in link_map.items():
            s.run("MERGE (:PDF {name:$n})", n=pdf_name)
            for l in links:
                parsed = urllib.parse.urlparse(l["uri"])
                domain = parsed.netloc or "unknown"
                s.run(
                    """
                    MERGE (d:LinkedDoc {url:$url})
                    ON CREATE SET d.status='unknown', d.domain=$domain
                    WITH d
                    MATCH (p:PDF {name:$pdf})
                    MERGE (p)-[:CITES {page:$page}]->(d)
                    """,
                    url=l["uri"],
                    pdf=pdf_name,
                    page=l["page"],
                    domain=domain
                )
    driver.close()


# 3. classify URL accessibility
def classify_url(url, timeout=5):
    """HEAD request → 'accessible' | 'unauthorized' | 'not_found' | 'other_ddd' | 'error'."""
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        if r.status_code == 200:
            return "accessible"
        if r.status_code in (401, 403):
            return "unauthorized"
        if r.status_code == 404:
            return "not_found"
        return f"other_{r.status_code}"
    except Exception:
        return "error"


def update_link_status(uri, user, pwd):
    """Set d.status for every LinkedDoc currently 'unknown'."""
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    with driver.session(database="neo4j") as s:
        for rec in s.run("MATCH (d:LinkedDoc {status:'unknown'}) RETURN d.url AS url"):
            s.run(
                "MATCH (d:LinkedDoc {url:$u}) SET d.status=$s",
                u=rec["url"],
                s=classify_url(rec["url"]),
            )
    driver.close()


# 4. download publicly accessible documents
def fetch_public_docs(uri, user, pwd, raw_dir: pathlib.Path):
    raw_dir.mkdir(exist_ok=True)
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    with driver.session(database="neo4j") as s:
        q = """
            MATCH (d:LinkedDoc {status:'accessible'})
            WHERE d.local_path IS NULL
            RETURN d.url AS url
        """
        for rec in s.run(q):
            url = rec["url"]
            try:
                fn = url.split("/")[-1] or "index.html"
                fp = raw_dir / fn
                fp.write_bytes(requests.get(url, timeout=10).content)
                s.run(
                    "MATCH (d:LinkedDoc {url:$u}) SET d.local_path=$p",
                    u=url,
                    p=str(fp),
                )
            except Exception as e:
                s.run(
                    "MATCH (d:LinkedDoc {url:$u}) SET d.status='fetch_error', d.error_message=$err",
                    u=url,
                    err=str(e))
    driver.close()


# 5. normalise raw downloads
def _html_to_text(html_path: pathlib.Path) -> str:
    soup = BeautifulSoup(
        html_path.read_text("utf-8", errors="ignore"), "html.parser"
    )
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def preprocess_downloaded_docs(raw_dir: pathlib.Path, clean_dir: pathlib.Path):
    clean_dir.mkdir(exist_ok=True)
    for f in raw_dir.iterdir():
        if f.suffix.lower() == ".pdf":
            (clean_dir / f.name).write_bytes(f.read_bytes())
        elif f.suffix.lower() in (".html", ".htm"):
            text = _html_to_text(f)
            print(f"Extracted {len(text)} chars from {f.name}")
            (clean_dir / (f.stem + ".txt")).write_text(text, encoding="utf-8")


# 6. add PDFs to neo4j
def add_main_pdfs_to_neo4j(uri, user, pwd, docs_dir):
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    with driver.session(database="neo4j") as s:
        for fn in os.listdir(docs_dir):
            if fn.lower().endswith(".pdf"):
                s.run("MERGE (:PDF {name:$n})", n=fn)
    driver.close()
