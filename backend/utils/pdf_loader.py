import fitz  # PyMuPDF
import re

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes.
    
    Uses 'blocks' extraction mode for better handling of tables and columns.
    Strips NUL (0x00) characters which PostgreSQL doesn't allow in text fields.
    """
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_text = []

    for page in pdf:
        # Extract text blocks - better for tables and multi-column layouts
        # Each block is a tuple: (x0, y0, x1, y1, "text", block_no, block_type)
        blocks = page.get_text("blocks")
        
        # Sort blocks by vertical position (y0), then horizontal (x0)
        # This helps preserve reading order for multi-column layouts
        blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
        
        for block in blocks:
            if block[6] == 0:  # Type 0 = text block
                block_text = block[4].strip()
                if block_text:
                    all_text.append(block_text)
    
    # Join with double newlines to preserve block separation
    text = "\n\n".join(all_text)
    
    # Clean up excessive whitespace while preserving paragraph structure
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove NUL characters that can appear in some PDFs
    # PostgreSQL TEXT type doesn't allow NUL bytes
    text = text.replace("\x00", "")
    
    return text.strip()