import json
import logging
import re
from pathlib import Path
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams
from rich.console import Console

console = Console()

logging.basicConfig(level=logging.INFO)

class PDFToJSONConverter:
    def __init__(self, min_paragraph_length=20):
        self.min_paragraph_length = min_paragraph_length
        self.filter_patterns = [
            r'^\s*•.*$',
            r'^\s*●.*$',
            r'^\s*\[.*\]\s*$',
            r'^\s*<.*>\s*$',
            r'^\s*Page\s*\d+\s*$',
            r'^\s*\d+\s*$',
            r'^Figure\s*\d+[\.\:]?.*$',
            r'^\s*Table\s*\d+[\.\:]?.*$',
            r'^[.\s]+$',
        ]
        self.compiled_filter_patterns = [re.compile(p, re.IGNORECASE) for p in self.filter_patterns]

    def should_filter_line(self, text):
        return any(pattern.match(text) for pattern in self.compiled_filter_patterns)

    def clean_text(self, text):
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def merge_short_paragraphs(self, paragraphs, min_length=50):
      merged = []
      current = ""

      for para in paragraphs:
          if len(current) == 0:
              current = para
          elif len(current) < min_length and not current.endswith(('.','?','!')):
              current += " " + para
          else:
              if len(current) >= self.min_paragraph_length:
                  merged.append(current)
              current = para

      if current and len(current) >= self.min_paragraph_length:
          merged.append(current)

      return merged

    def extract_text_from_pdf(self, pdf_path):
        try:
            text = extract_text(pdf_path, laparams=LAParams())
            console.print(f"Processing: {pdf_path}")
            raw_paragraphs = re.split(r'\n\s*\n', text)
            paragraphs = {}
            current_id = 1

            for para in raw_paragraphs:
                lines = para.split('\n')
                filtered_lines = []
                for line in lines:
                    cleaned_line = self.clean_text(line)
                    if cleaned_line and not self.should_filter_line(cleaned_line):
                        filtered_lines.append(cleaned_line)

                if filtered_lines:
                    cleaned_para = ' '.join(filtered_lines)
                    if len(cleaned_para) >= self.min_paragraph_length:
                        key = f"Paragraph_{current_id}"
                        paragraphs[key] = cleaned_para
                        current_id += 1

            if paragraphs:
                merged_paras = self.merge_short_paragraphs(list(paragraphs.values()))
                paragraphs = {f"Paragraph_{i+1}": para for i, para in enumerate(merged_paras)}

            return paragraphs

        except Exception as e:
            console.print(f"[bold red]Error processing {pdf_path}:[/bold red] {e}")
            return None

    def convert_pdf_to_json(self, pdf_path, output_path=None):
        paragraphs = self.extract_text_from_pdf(pdf_path)
        if paragraphs is None:
            return None

        if output_path is None:
            output_path = Path(pdf_path).with_suffix('.json')

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(paragraphs, f, indent=4, ensure_ascii=False)

        console.print(f"[green]Successfully converted[/green] {pdf_path} to {output_path}")
        return paragraphs

# Example Usage (Adapted for Codespaces/Same Directory)
if __name__ == '__main__':
    converter = PDFToJSONConverter()

    # Get the current working directory (where the script is running)
    current_dir = Path(__file__).parent

    # Define your test PDFs *relative to the current directory*.
    test_pdfs = [
        current_dir / 'AIStransceiver_Commercial manual.pdf',  # Assumes PDF is in the same folder
        # Add more PDFs here, relative to current_dir:
        # current_dir / 'another_document.pdf',
    ]

    for pdf_file in test_pdfs:
        if pdf_file.exists():
            converter.convert_pdf_to_json(str(pdf_file))  # Pass string path to pdfminer.six
        else:
            console.print(f"[bold red]File not found: {pdf_file}[/bold red]")