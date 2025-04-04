# Refactoring Plan: PDF Parser (pdf2image to PyMuPDF)

**Goal:** Modify the `PDFToJSONConverter` class in `main.py` to use `PyMuPDF` for rendering PDF pages to images for OCR, replacing the `pdf2image`/Poppler dependency.

**Detailed Plan:**

1.  **Dependency Management:**
    *   **Update `requirements.txt`:**
        *   Remove the line containing `pdf2image`.
        *   Add a line for `PyMuPDF` (e.g., `PyMuPDF>=1.23.0`).
    *   **(External Step - User Action)** **Update `Dockerfile` (if applicable):**
        *   Remove any steps that install `poppler-utils`.
        *   Ensure `tesseract-ocr` and necessary language packs (like `tesseract-ocr-eng`) are still installed.
        *   The `pip install -r requirements.txt` step will now install `PyMuPDF`.

2.  **Code Modifications in `main.py`:**
    *   **Imports:**
        *   Remove `from pdf2image import convert_from_path`.
        *   Remove `from pdf2image.pdf2image import pdfinfo_from_path`.
        *   Add `import fitz`.
    *   **Modify `extract_text_with_ocr` Method:**
        *   **Initialize `doc`:** Add `doc = None` before the main `try` block.
        *   **Open PDF & Get Page Count:** Replace `pdfinfo_from_path` logic with `doc = fitz.open(pdf_path)` and `total_pages = doc.page_count`.
        *   **Logging:** Keep batch-based logging.
        *   **Remove `convert_from_path` Call:** Delete the call.
        *   **Adapt Loop Structure:**
            *   Keep the outer batch loop.
            *   Replace the inner image loop with a page number loop for the current batch: `for page_num in range(start_page, min(start_page + batch_size, total_pages + 1)):`.
        *   **Page Processing within Inner Loop:**
            *   Load page: `page = doc.load_page(page_num - 1)`
            *   Render to pixmap: `pix = page.get_pixmap(dpi=self.dpi)`
            *   Convert Pixmap to PIL Image (add `try...except...finally` block for conversion).
            *   Apply Image Resizing logic to the PIL `img`.
            *   Perform OCR: Pass the PIL `img` to `pytesseract.image_to_string`.
            *   Keep Text Processing logic.
            *   **Memory Management:** Add `img.close()` and `img = None` after OCR.
        *   **Remove Batch Image Cleanup:** Delete `images = None`, `gc.collect()`.
        *   **Ensure PDF Closure:** Add a `finally` block to ensure `doc.close()`.

3.  **Testing (Post-Implementation):**
    *   Run the script with various PDF files.
    *   Verify JSON output and OCR functionality.
    *   Monitor memory usage.

**Plan Visualization (Mermaid):**

```mermaid
graph TD
    subgraph Preparation
        A[Update requirements.txt: Remove pdf2image, Add PyMuPDF]
        B[User Action: Update Dockerfile (if exists) - Remove Poppler]
    end

    subgraph Code Changes (main.py)
        C[Update Imports: Add 'import fitz', Remove 'pdf2image' imports]
        D[Modify 'extract_text_with_ocr' method]
        D --> D1[Open PDF with 'fitz.open()' before loop]
        D --> D2[Get page count using 'doc.page_count']
        D --> D3[Keep outer batch loop for logging]
        D --> D4[Remove 'convert_from_path()' call]
        D --> D5[Replace inner image loop with page number loop (using batch range)]
        D --> D6[Inside inner loop: Load page ('doc.load_page')]
        D --> D7[Inside inner loop: Render page to pixmap ('page.get_pixmap')]
        D --> D8[Inside inner loop: Convert pixmap to PIL Image ('Image.frombytes')]
        D --> D9[Inside inner loop: Apply existing resize logic to PIL Image]
        D --> D10[Inside inner loop: Pass PIL Image to 'pytesseract.image_to_string']
        D --> D11[Inside inner loop: Keep text processing/paragraph logic]
        D --> D12[Inside inner loop: Add cleanup for PIL Image ('img.close()')]
        D --> D13[Remove batch image list cleanup code]
        D --> D14[Add 'finally' block to ensure 'doc.close()']
    end

    subgraph Verification
        E[Test with various PDF types (text, image, mixed)]
        F[Verify JSON output and OCR functionality]
        G[Monitor memory usage]
    end

    Preparation --> Code Changes --> Verification