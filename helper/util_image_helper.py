import fitz  # PyMuPDF
from pathlib import Path, PosixPath
from ollama import Client
from typing import List, Tuple
from config import config
import logging

from prompt_templates.image_prompt_template import IMAGE_DESCRIPTION_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 1. Extract images from PDF pages and return image paths with page numbers
def extract_images_from_pdf(pdf_path: str, output_dir: Path, min_width=100, min_height=100, min_area=10000) -> List[Tuple[Path, int]]:
    """
    Extracts non-trivial images from a PDF file. Skips small or decorative images.
    Returns a list of tuples: (image_path, page_number).
    """
    from PIL import Image
    import io

    # 1.1 Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    image_paths = []

    # 1.2 Open the PDF file
    doc = fitz.open(pdf_path)

    # 1.3 Iterate through each page and extract valid images
    for i, page in enumerate(doc):
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            ext = base_image["ext"]

            try:
                image = Image.open(io.BytesIO(img_bytes))
                width, height = image.size
                area = width * height

                # 1.4 Skip logos, stripes, or low-content images
                if width < min_width or height < min_height or area < min_area:
                    continue

                img_name = f"{Path(pdf_path).stem}_page{i+1}_img{img_index+1}.{ext}"
                img_path = output_dir / img_name
                image.save(img_path)

                image_paths.append((img_path, i + 1))  # Store image and page number

            except Exception as e:
                logger.warning(f"Failed to process or save image {xref}: {e}")

    logger.info(f"Extracted {len(image_paths)} filtered images from {pdf_path}")
    return image_paths


# 2. Send image to Ollama's LLaVA model and get a descriptive caption
def describe_image_with_llava(image_path: Path, prompt: str = IMAGE_DESCRIPTION_PROMPT) -> str:
    client = Client(host=f"http://{config.OLLAMA_HOST}:{config.OLLAMA_PORT}")

    # 2.1 Read image bytes
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # 2.2 Perform visual question answering using LLaVA
    try:
        response = client.chat(
            model=config.OLLAMA_VLM_MODEL,
            messages=[{"role": "user", "content": prompt, "images": [image_bytes]}],
        )
        return response['message']['content']

    except Exception as e:
        logger.error(f"Failed to describe image {image_path.name}: {e}")
        return "Error processing image."
