# pdfparser

## Description
This project is a PDF parser that extracts text and other information from PDF files. It supports extracting text, images, and metadata from PDF files. The parser can handle encrypted PDFs and provides options for extracting specific pages or ranges of pages.

## Features
- Extract text from PDF files
- Extract images from PDF files
- Extract metadata from PDF files
- Handle encrypted PDFs
- Extract specific pages or ranges of pages

## Installation
To install the required dependencies, run:
```
pip install -r requirements.txt
```

## Usage
To use the PDF parser, run:
```
python pdfparser.py <path_to_pdf_file>
```

## Examples
To extract text from a PDF file:
```
python pdfparser.py --text <path_to_pdf_file>
```

To extract images from a PDF file:
```
python pdfparser.py --images <path_to_pdf_file>
```

To extract metadata from a PDF file:
```
python pdfparser.py --metadata <path_to_pdf_file>
```

To extract specific pages from a PDF file:
```
python pdfparser.py --pages 1-3 <path_to_pdf_file>
```

## Troubleshooting
If you encounter any issues, please check the following:
- Ensure you have installed all the required dependencies.
- Verify the path to the PDF file is correct.
- Check if the PDF file is encrypted and provide the correct password if needed.

## License
This project is licensed under the MIT License.