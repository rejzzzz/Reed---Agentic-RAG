"""
Multimodal PDF Processor
Handles extraction of text, images, and tables from PDF documents
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import fitz  # PyMuPDF
import PyPDF2
import pdfplumber
import pytesseract
from PIL import Image
import io
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    """Container for extracted content from PDF"""
    text: str
    page_number: int
    content_type: str  # 'text', 'table', 'image'
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    metadata: Dict[str, Any]


@dataclass
class DocumentInfo:
    """Container for document-level information"""
    filename: str
    total_pages: int
    file_size: int
    extracted_content: List[ExtractedContent]
    processing_stats: Dict[str, Any]


class MultimodalPDFProcessor:
    """
    Processes PDF documents to extract text, images, and tables
    while preserving precise location information
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.text_config = config.get('text_extraction', {})
        self.table_config = config.get('table_extraction', {})
        self.image_config = config.get('image_processing', {})
        
        # Setup directories
        self.output_dir = Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("MultimodalPDFProcessor initialized")
    
    def process_directory(self, pdf_directory: str) -> Dict[str, Any]:
        """
        Process all PDF files in a directory
        
        Args:
            pdf_directory: Path to directory containing PDF files
            
        Returns:
            Dictionary containing processing results
        """
        pdf_dir = Path(pdf_directory)
        if not pdf_dir.exists():
            raise FileNotFoundError(f"PDF directory {pdf_dir} does not exist")
        
        pdf_files = list(pdf_dir.glob("*.pdf"))
        if not pdf_files:
            raise ValueError(f"No PDF files found in {pdf_dir}")
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        results = {
            'documents': [],
            'total_pages': 0,
            'total_files': len(pdf_files),
            'processing_stats': {}
        }
        
        for pdf_file in pdf_files:
            try:
                doc_info = self.process_single_pdf(pdf_file)
                
                # Convert DocumentInfo to dictionary with proper serialization
                doc_dict = {
                    'filename': doc_info.filename,
                    'total_pages': doc_info.total_pages,
                    'file_size': doc_info.file_size,
                    'processing_stats': doc_info.processing_stats,
                    'extracted_content': []
                }
                
                # Convert ExtractedContent objects to dictionaries
                for content in doc_info.extracted_content:
                    # Convert bbox to simple tuple if it's a Rect object
                    bbox = content.bbox
                    if hasattr(bbox, '__iter__') and not isinstance(bbox, (list, tuple)):
                        # It's likely a Rect object, convert to tuple
                        bbox = tuple(bbox) if hasattr(bbox, '__iter__') else (0, 0, 0, 0)
                    elif bbox is None:
                        bbox = (0, 0, 0, 0)
                    
                    content_dict = {
                        'text': content.text,
                        'page_number': content.page_number,
                        'content_type': content.content_type,
                        'bbox': bbox,
                        'metadata': content.metadata or {}
                    }
                    doc_dict['extracted_content'].append(content_dict)
                
                results['documents'].append(doc_dict)
                results['total_pages'] += doc_info.total_pages
                
                logger.info(f"Processed {pdf_file.name}: {doc_info.total_pages} pages")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {str(e)}")
                continue
        
        # Save processing results - no need for additional conversion since we already did it above
        results_file = self.output_dir / "processing_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Processing complete. Total pages: {results['total_pages']}")
        return results
    
    def process_single_pdf(self, pdf_path: Path) -> DocumentInfo:
        """
        Process a single PDF file to extract all content types
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            DocumentInfo object containing all extracted content
        """
        logger.info(f"Processing PDF: {pdf_path.name}")
        
        extracted_content = []
        processing_stats = {
            'text_blocks': 0,
            'tables': 0,
            'images': 0,
            'pages_processed': 0
        }
        
        # Get basic document info
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            file_size = pdf_path.stat().st_size
        
        # Process with PyMuPDF for comprehensive extraction
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text with positions
            text_content = self._extract_text_with_positions(page, page_num + 1)
            extracted_content.extend(text_content)
            processing_stats['text_blocks'] += len(text_content)
            
            # Extract images
            image_content = self._extract_images(page, page_num + 1)
            extracted_content.extend(image_content)
            processing_stats['images'] += len(image_content)
            
            processing_stats['pages_processed'] += 1
        
        doc.close()
        
        # Extract tables using pdfplumber
        table_content = self._extract_tables_pdfplumber(pdf_path)
        extracted_content.extend(table_content)
        processing_stats['tables'] += len(table_content)
        
        doc_info = DocumentInfo(
            filename=pdf_path.name,
            total_pages=total_pages,
            file_size=file_size,
            extracted_content=extracted_content,
            processing_stats=processing_stats
        )
        
        return doc_info
    
    def _extract_text_with_positions(self, page, page_number: int) -> List[ExtractedContent]:
        """Extract text with precise positioning information"""
        text_content = []
        
        # Get text blocks with positions
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
            if "lines" in block:  # Text block
                block_text = ""
                bbox = block["bbox"]
                
                for line in block["lines"]:
                    for span in line["spans"]:
                        block_text += span["text"]
                    block_text += "\n"
                
                if block_text.strip():
                    # Convert bbox to tuple for JSON serialization
                    bbox_tuple = tuple(bbox) if hasattr(bbox, '__iter__') else (0, 0, 0, 0)
                    
                    content = ExtractedContent(
                        text=block_text.strip(),
                        page_number=page_number,
                        content_type="text",
                        bbox=bbox_tuple,
                        metadata={
                            "font_info": self._extract_font_info(block),
                            "block_type": "text"
                        }
                    )
                    text_content.append(content)
        
        return text_content
    
    def _extract_images(self, page, page_number: int) -> List[ExtractedContent]:
        """Extract images and perform OCR if configured"""
        image_content = []
        
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            try:
                # Get image
                xref = img[0]
                base_image = page.parent.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))
                
                # Check minimum size
                min_size = self.image_config.get('min_image_size', [100, 100])
                if image.size[0] < min_size[0] or image.size[1] < min_size[1]:
                    continue
                
                # Get image position on page
                image_rects = page.get_image_rects(xref)
                bbox = image_rects[0] if image_rects else (0, 0, 0, 0)
                # Convert to tuple for JSON serialization
                bbox_tuple = tuple(bbox) if hasattr(bbox, '__iter__') else (0, 0, 0, 0)
                
                # Perform OCR if enabled
                ocr_text = ""
                if self.image_config.get('ocr_images', False):
                    try:
                        ocr_text = pytesseract.image_to_string(image)
                    except Exception as e:
                        logger.warning(f"OCR failed for image {img_index} on page {page_number}: {e}")
                
                content = ExtractedContent(
                    text=ocr_text,
                    page_number=page_number,
                    content_type="image",
                    bbox=bbox_tuple,
                    metadata={
                        "image_index": img_index,
                        "image_size": image.size,
                        "image_format": base_image.get("ext", "unknown"),
                        "has_ocr_text": bool(ocr_text.strip())
                    }
                )
                image_content.append(content)
                
            except Exception as e:
                logger.warning(f"Error processing image {img_index} on page {page_number}: {e}")
                continue
        
        return image_content
    
    def _extract_tables_pdfplumber(self, pdf_path: Path) -> List[ExtractedContent]:
        """Extract tables using pdfplumber"""
        table_content = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    
                    for table_index, table in enumerate(tables):
                        if table and len(table) > 1:  # Valid table with header + data
                            # Convert table to text representation
                            table_text = self._table_to_text(table)
                            
                            # Get table bbox (approximate)
                            bbox = self._estimate_table_bbox(page, table)
                            
                            content = ExtractedContent(
                                text=table_text,
                                page_number=page_num,
                                content_type="table",
                                bbox=bbox,
                                metadata={
                                    "table_index": table_index,
                                    "rows": len(table),
                                    "columns": len(table[0]) if table else 0,
                                    "extraction_method": "pdfplumber"
                                }
                            )
                            table_content.append(content)
                            
        except Exception as e:
            logger.error(f"Error extracting tables from {pdf_path.name}: {e}")
        
        return table_content
    
    def _table_to_text(self, table: List[List[str]]) -> str:
        """Convert table to readable text format"""
        if not table:
            return ""
        
        # Create a formatted text representation
        text_lines = []
        
        # Header
        if table[0]:
            header = " | ".join(str(cell) if cell else "" for cell in table[0])
            text_lines.append(header)
            text_lines.append("-" * len(header))
        
        # Data rows
        for row in table[1:]:
            if row:
                row_text = " | ".join(str(cell) if cell else "" for cell in row)
                text_lines.append(row_text)
        
        return "\n".join(text_lines)
    
    def _estimate_table_bbox(self, page, table) -> Tuple[float, float, float, float]:
        """Estimate bounding box for extracted table"""
        # This is a simplified estimation
        # In practice, you might want to use table.bbox if available
        page_width = page.width
        page_height = page.height
        
        # Return a rough estimate (could be improved with more sophisticated detection)
        return (0, 0, page_width, page_height)
    
    def _extract_font_info(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Extract font information from text block"""
        font_info = {
            "fonts": [],
            "sizes": [],
            "styles": []
        }
        
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    font_info["fonts"].append(span.get("font", ""))
                    font_info["sizes"].append(span.get("size", 0))
                    font_info["styles"].append({
                        "bold": "bold" in span.get("font", "").lower(),
                        "italic": "italic" in span.get("font", "").lower()
                    })
        
        return font_info
    
    def save_extracted_content(self, doc_info: DocumentInfo) -> str:
        """Save extracted content to JSON file"""
        output_file = self.output_dir / f"{doc_info.filename}_extracted.json"
        
        # Convert to serializable format
        content_data = {
            "document_info": {
                "filename": doc_info.filename,
                "total_pages": doc_info.total_pages,
                "file_size": doc_info.file_size,
                "processing_stats": doc_info.processing_stats
            },
            "extracted_content": [
                {
                    "text": content.text,
                    "page_number": content.page_number,
                    "content_type": content.content_type,
                    "bbox": content.bbox,
                    "metadata": content.metadata
                }
                for content in doc_info.extracted_content
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(content_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Extracted content saved to {output_file}")
        return str(output_file)


# Example usage and testing
if __name__ == "__main__":
    # Basic configuration for testing
    config = {
        'text_extraction': {
            'preserve_layout': True,
            'extract_images': True,
            'ocr_enabled': True,
            'ocr_language': 'eng'
        },
        'table_extraction': {
            'method': 'pdfplumber',
            'table_areas': None,
            'edge_tolerance': 50
        },
        'image_processing': {
            'extract_images': True,
            'ocr_images': True,
            'image_description': True,
            'min_image_size': [100, 100]
        }
    }
    
    # Create processor and test
    processor = MultimodalPDFProcessor(config)
    
    # Test with sample PDFs (if available)
    pdf_dir = "data/pdfs"
    if Path(pdf_dir).exists():
        results = processor.process_directory(pdf_dir)
        print(f"Processed {results['total_files']} files, {results['total_pages']} pages total")
    else:
        print(f"PDF directory {pdf_dir} not found. Please add PDF files to test the processor.")
