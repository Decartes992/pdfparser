import json
import re
from pathlib import Path
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextContainer
from rich.console import Console

console = Console()

class PDFToJSONConverter:
    def __init__(self, min_paragraph_length=20):
        self.min_paragraph_length = min_paragraph_length
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
        """Clean text by removing extra spaces and stripping."""
        text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with one
        return text.strip()

    def should_filter_line(self, text):
        """Check if text matches any filter patterns to exclude it."""
        return any(pattern.match(text) for pattern in self.compiled_filter_patterns)

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF as a list of paragraphs."""
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
            return paragraphs
        except Exception as e:
            console.print(f"[bold red]Error processing {pdf_path}:[/bold red] {e}")
            return None

    def convert_pdf_to_json(self, pdf_path, output_path=None):
        """Convert PDF text to JSON with paragraph1, paragraph2, etc."""
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
    converter = PDFToJSONConverter()
    current_dir = Path(__file__).parent
    # Find all PDF files in the current directory
    pdf_files = list(current_dir.glob('*.pdf'))
    
    if not pdf_files:
        console.print("[bold yellow]No PDF files found in the directory.[/bold yellow]")
    else:
        for pdf_file in pdf_files:
            converter.convert_pdf_to_json(str(pdf_file))