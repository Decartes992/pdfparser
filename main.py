import json  # For handling JSON data
import re  # For regular expressions
from pathlib import Path  # For handling file paths
import fitz # For PyMuPDF PDF handling
from pdfminer.high_level import extract_pages  # For extracting pages from PDF
from pdfminer.layout import LAParams, LTTextContainer  # For layout analysis
from rich.console import Console  # For colorful console output
import pytesseract  # For OCR capabilities
from PIL import Image  # For image processing
import io  # For byte stream handling
import os  # For OS operations
import gc # For garbage collection

console = Console()  # Initialize console

class PDFToJSONConverter:
    """
    A class to convert PDF files to JSON format, extracting text and organizing it into paragraphs.
    """
    def __init__(self, min_paragraph_length=20, ocr_mode='auto', ocr_language='eng', dpi=300):
        """
        Initializes the converter with a minimum paragraph length.

        Args:
            min_paragraph_length (int): Minimum length of a paragraph to be included in the output.
            ocr_mode (str): OCR mode - 'auto', 'always', or 'never'.
            ocr_language (str): Language for OCR (e.g., 'eng', 'fra', 'deu').
            dpi (int): DPI for PDF to image conversion for OCR.
        """
        self.min_paragraph_length = min_paragraph_length
        self.ocr_mode = ocr_mode
        self.ocr_language = ocr_language
        self.dpi = dpi
        
        # Patterns to filter out unwanted text (e.g., page numbers, captions)
        self.filter_patterns = [
            r'^\s*•.*$',                     # Bullet points
            r'^\s*●.*$',                     # Alternative bullet points
            r'^\s*\[.*\]\s*$',              # Bracketed lines
            r'^\s*<.*>\s*$',                # Angle-bracketed lines
            r'^\s*Page\s*\d+\s*$',          # Page numbers
            r'^\s*\d+\s*$',                 # Lone numbers
            r'^Figure\s*\d+[\.\:]?.*$',     # Figure captions
            r'^\s*Table\s*\d+[\.\:]?.*$',   # Table captions
            r'^[.\s]+$',                    # Lines with only dots/spaces
            r'^\s*\d+(\.\d+)*\s+\w+(\s+\w+){0,4}\.{3,}.*\d+\s*$',  # TOC entries
        ]
        self.compiled_filter_patterns = [re.compile(p, re.IGNORECASE) for p in self.filter_patterns]

    def clean_text(self, text):
        """
        Clean text by removing extra spaces and stripping.

        Args:
            text (str): Text to clean.

        Returns:
            str: Cleaned text.
        """
        text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with one
        return text.strip()

    def should_filter_line(self, text):
        """
        Check if text matches any filter patterns to exclude it.

        Args:
            text (str): Text to check.

        Returns:
            bool: True if the text should be filtered out, False otherwise.
        """
        return any(pattern.match(text) for pattern in self.compiled_filter_patterns)

    def extract_text_with_ocr(self, pdf_path):
        """
        Extract text from PDF using OCR with batched processing to manage memory.
        
        Args:
            pdf_path (str): Path to the PDF file.
            
        Returns:
            list: List of extracted paragraphs.
        """
        paragraphs = []
        doc = None # Initialize doc to ensure it's available in finally block
        try:
            # Open PDF and get page count using PyMuPDF
            doc = fitz.open(pdf_path)
            total_pages = doc.page_count
            
            console.print(f"[yellow]Processing {pdf_path} with OCR - {total_pages} pages total[/yellow]")
            
            # Process pages in batches to manage memory
            batch_size = 5  # Adjust based on available memory
            
            for start_page in range(1, total_pages + 1, batch_size):
                end_page = min(start_page + batch_size - 1, total_pages)
                console.print(f"[yellow]Processing pages {start_page}-{end_page} of {total_pages}[/yellow]")

                # Process pages within the current batch range
                for page_num in range(start_page, min(start_page + batch_size, total_pages + 1)):
                    console.print(f"[yellow]OCR processing page {page_num}/{total_pages}[/yellow]")
                    img = None # Initialize img for this page iteration
                    pix = None # Initialize pix for this page iteration
                    try:
                        # Load page using PyMuPDF (0-indexed)
                        page = doc.load_page(page_num - 1)
                        
                        # Render page to pixmap
                        pix = page.get_pixmap(dpi=self.dpi)
                        
                        # Convert pixmap to PIL Image
                        try:
                            if pix.alpha:
                                img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
                            else:
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        except Exception as img_conv_e:
                            console.print(f"[bold red]Error converting page {page_num} pixmap to PIL Image: {img_conv_e}[/bold red]")
                            continue # Skip this page if conversion fails
                        finally:
                             pix = None # Ensure pixmap is dereferenced even if conversion fails

                        # Free memory by resizing the image if it's very large
                        width, height = img.size
                        if width > 3000 or height > 3000:
                            scale_factor = min(3000/width, 3000/height)
                            new_width = int(width * scale_factor)
                            new_height = int(height * scale_factor)
                            img = img.resize((new_width, new_height), Image.LANCZOS)
                            
                        # Extract text from the image using pytesseract
                        text = pytesseract.image_to_string(img, lang=self.ocr_language)
                        
                        # Process the extracted text (same logic as before)
                        lines = text.split('\n')
                        current_paragraph = []
                        
                        for line in lines:
                            cleaned_line = self.clean_text(line)
                            if not cleaned_line or self.should_filter_line(cleaned_line):
                                if current_paragraph:
                                    paragraph_text = ' '.join(current_paragraph)
                                    if len(paragraph_text) >= self.min_paragraph_length:
                                        paragraphs.append(paragraph_text)
                                    current_paragraph = []
                            else:
                                current_paragraph.append(cleaned_line)
                        
                        # Add the last paragraph if it exists
                        if current_paragraph:
                            paragraph_text = ' '.join(current_paragraph)
                            if len(paragraph_text) >= self.min_paragraph_length:
                                paragraphs.append(paragraph_text)
                                
                    except Exception as page_e:
                        console.print(f"[bold red]Error OCR processing page {page_num}: {page_e}[/bold red]")
                        # Continue to the next page even if one fails
                    finally:
                        # Clean up PIL image object for the current page
                        if img:
                            img.close()
                            img = None
                        # Force garbage collection periodically (after each page in this case)
                        # Note: gc import moved to top level if not already there
                        # gc is imported at the top level
                        gc.collect()

                # No batch-level image list to clear anymore
            
            console.print(f"[green]OCR completed: extracted {len(paragraphs)} paragraphs[/green]")
            return paragraphs
            
        except Exception as e:
            console.print(f"[bold red]Error processing {pdf_path} with OCR: {e}[/bold red]")
            return None
        finally:
            # Ensure the document is closed
            if doc:
                doc.close()
                console.print(f"[dim]Closed PDF document: {pdf_path}[/dim]")

    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from PDF as a list of paragraphs.
        Falls back to OCR if needed based on ocr_mode setting.

        Args:
            pdf_path (str): Path to the PDF file.

        Returns:
            list: List of extracted paragraphs.
        """
        if self.ocr_mode == 'always':
            return self.extract_text_with_ocr(pdf_path)
            
        # Try regular text extraction first
        paragraphs = []
        try:
            # Iterate through PDF pages
            for page_layout in extract_pages(pdf_path, laparams=LAParams()):
                # Iterate through layout elements on the page
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        # Get the full text from the container (e.g., LTTextBox)
                        text = element.get_text()
                        cleaned_text = self.clean_text(text)
                        # Add text as a paragraph if it’s not empty and not filtered
                        if cleaned_text and not self.should_filter_line(cleaned_text):
                            paragraphs.append(cleaned_text)
            
            # If in auto mode and no text found, try OCR
            if self.ocr_mode == 'auto' and (not paragraphs or len(''.join(paragraphs)) < 100):
                console.print(f"[yellow]Limited text found in {pdf_path}. Trying OCR...[/yellow]")
                ocr_paragraphs = self.extract_text_with_ocr(pdf_path)
                if ocr_paragraphs:
                    return ocr_paragraphs
                
            return paragraphs
        except Exception as e:
            console.print(f"[bold red]Error processing {pdf_path}:[/bold red] {e}")
            
            # If text extraction failed and OCR is allowed, try OCR
            if self.ocr_mode != 'never':
                console.print("[yellow]Falling back to OCR...[/yellow]")
                return self.extract_text_with_ocr(pdf_path)
                
            return None

    def convert_pdf_to_json(self, pdf_path, output_path=None):
        """
        Convert PDF text to JSON with paragraph1, paragraph2, etc.

        Args:
            pdf_path (str): Path to the PDF file.
            output_path (str, optional): Path to save the JSON output. Defaults to None.

        Returns:
            dict: Dictionary containing the extracted paragraphs.
        """
        paragraphs = self.extract_text_from_pdf(pdf_path)
        if paragraphs is None:
            return None

        # Create a dictionary with paragraph keys
        paragraph_dict = {f"paragraph{i+1}": para for i, para in enumerate(paragraphs)}

        # Set default output path if not provided
        if output_path is None:
            output_path = Path(pdf_path).with_suffix('.json')

        # Write to JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(paragraph_dict, f, indent=4, ensure_ascii=False)

        console.print(f"[green]Successfully converted[/green] {pdf_path} to {output_path}")
        return paragraph_dict

# Example Usage
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert PDF to JSON with optional OCR')
    parser.add_argument('--input', '-i', help='Path to specific PDF file to process')
    parser.add_argument('--dpi', type=int, default=200, help='DPI for OCR image conversion (lower for memory efficiency)')
    parser.add_argument('--ocr', choices=['auto', 'always', 'never'], default='auto', help='OCR mode')
    parser.add_argument('--batch', type=int, default=5, help='Number of pages to process at once')
    parser.add_argument('--lang', default='eng', help='OCR language')
    args = parser.parse_args()
    
    converter = PDFToJSONConverter(ocr_mode=args.ocr, ocr_language=args.lang, dpi=args.dpi)
    
    if args.input:
        # Process a specific file
        input_path = Path(args.input)
        if input_path.exists() and input_path.suffix.lower() == '.pdf':
            converter.convert_pdf_to_json(str(input_path))
        else:
            console.print(f"[bold red]File not found or not a PDF: {args.input}[/bold red]")
    else:
        # Process all PDFs in the current directory
        current_dir = Path(__file__).parent
        pdf_files = list(current_dir.glob('*.pdf'))
        
        if not pdf_files:
            console.print("[bold yellow]No PDF files found in the directory.[/bold yellow]")
        else:
            for pdf_file in pdf_files:
                converter.convert_pdf_to_json(str(pdf_file))