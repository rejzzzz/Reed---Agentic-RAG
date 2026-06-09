"""
Semantic Chunking Module
Implements intelligent chunking strategies that preserve semantic meaning
"""

import logging
import json
import spacy
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import re
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SemanticChunk:
    """Container for a semantic chunk with metadata"""
    chunk_id: str
    text: str
    chunk_type: str  # 'text', 'table', 'image'
    source_document: str
    page_numbers: List[int]
    bbox_info: List[Tuple[float, float, float, float]]
    embedding: np.ndarray = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'chunk_id': self.chunk_id,
            'text': self.text,
            'chunk_type': self.chunk_type,
            'source_document': self.source_document,
            'page_numbers': self.page_numbers,
            'bbox_info': self.bbox_info,
            'embedding': self.embedding.tolist() if self.embedding is not None else None,
            'metadata': self.metadata or {}
        }


class SemanticChunker:
    """
    Advanced semantic chunking that respects document structure and meaning
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.chunk_size = self.config.get('chunk_size', settings.CHUNK_SIZE)
        self.chunk_overlap = self.config.get('chunk_overlap', settings.CHUNK_OVERLAP)
        self.min_chunk_size = self.config.get('min_chunk_size', settings.MIN_CHUNK_SIZE)
        self.max_chunk_size = self.config.get('max_chunk_size', settings.MAX_CHUNK_SIZE)
        self.similarity_threshold = self.config.get('similarity_threshold', settings.CHUNK_SIMILARITY_THRESHOLD)
        
        # Initialize components
        self._load_nlp_model()
        self._load_embedding_model()
        
        # Setup output directory
        self.output_dir = Path(settings.PROCESSED_DATA_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("SemanticChunker initialized")
    
    def _load_nlp_model(self):
        """Load spaCy model for sentence segmentation"""
        try:
            self.nlp = spacy.load(settings.SPACY_MODEL)
            logger.info(f"Loaded spaCy {settings.SPACY_MODEL} model")
        except OSError:
            logger.error(f"spaCy {settings.SPACY_MODEL} model not found. Run: python -m spacy download {settings.SPACY_MODEL}")
            raise
    
    def _load_embedding_model(self):
        """Load sentence transformer for semantic similarity"""
        model_name = self.config.get('embeddings', {}).get('model_name', settings.EMBEDDING_MODEL)
        self.embedding_model = SentenceTransformer(model_name)
        logger.info(f"Loaded embedding model: {model_name}")
    
    def process_documents(self, documents: List[Dict[str, Any]]) -> List[SemanticChunk]:
        """
        Process extracted document content into semantic chunks
        
        Args:
            documents: List of document dictionaries from PDF processor
            
        Returns:
            List of SemanticChunk objects
        """
        logger.info(f"Processing {len(documents)} documents for semantic chunking")
        
        all_chunks = []
        
        for doc in documents:
            doc_chunks = self._process_single_document(doc)
            all_chunks.extend(doc_chunks)
            logger.info(f"Created {len(doc_chunks)} chunks from {doc['filename']}")
        
        # Generate embeddings for all chunks
        logger.info("Generating embeddings for all chunks...")
        self._generate_embeddings(all_chunks)
        
        # Save chunks to file
        self._save_chunks(all_chunks)
        
        logger.info(f"Total semantic chunks created: {len(all_chunks)}")
        return all_chunks
    
    def _process_single_document(self, document: Dict[str, Any]) -> List[SemanticChunk]:
        """Process a single document into semantic chunks"""
        filename = document['filename']
        extracted_content = document['extracted_content']
        
        chunks = []
        
        # Group content by type and process differently
        text_content = [c for c in extracted_content if c['content_type'] == 'text']
        table_content = [c for c in extracted_content if c['content_type'] == 'table']
        image_content = [c for c in extracted_content if c['content_type'] == 'image']
        
        # Process text content with semantic chunking
        text_chunks = self._chunk_text_content(text_content, filename)
        chunks.extend(text_chunks)
        
        # Process tables (usually keep as separate chunks)
        table_chunks = self._chunk_table_content(table_content, filename)
        chunks.extend(table_chunks)
        
        # Process images (with OCR text if available)
        image_chunks = self._chunk_image_content(image_content, filename)
        chunks.extend(image_chunks)
        
        return chunks
    
    def _chunk_text_content(self, text_content: List[Dict], filename: str) -> List[SemanticChunk]:
        """Apply semantic chunking to text content"""
        if not text_content:
            return []
        
        # Combine all text content by page for better context
        page_texts = {}
        for content in text_content:
            page_num = content['page_number']
            if page_num not in page_texts:
                page_texts[page_num] = []
            page_texts[page_num].append(content)
        
        chunks = []
        chunk_counter = 0
        
        for page_num in sorted(page_texts.keys()):
            page_content = page_texts[page_num]
            
            # Combine text from the page
            page_text = "\n\n".join([c['text'] for c in page_content])
            
            if len(page_text.strip()) < self.min_chunk_size:
                continue
            
            # Apply semantic chunking to page text
            page_chunks = self._semantic_split_text(
                page_text, 
                page_num, 
                page_content,
                filename,
                chunk_counter
            )
            chunks.extend(page_chunks)
            chunk_counter += len(page_chunks)
        
        return chunks
    
    def _semantic_split_text(self, text: str, page_num: int, content_list: List[Dict], 
                           filename: str, start_counter: int) -> List[SemanticChunk]:
        """Split text using semantic similarity"""
        
        # First, split into sentences
        doc = self.nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        if not sentences:
            return []
        
        # Group sentences into chunks based on semantic similarity
        chunks = []
        current_chunk = []
        current_length = 0
        
        for i, sentence in enumerate(sentences):
            sentence_length = len(sentence)
            
            # Check if adding this sentence would exceed max chunk size
            if current_length + sentence_length > self.max_chunk_size and current_chunk:
                # Finalize current chunk
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunk = self._create_text_chunk(
                        chunk_text, 
                        page_num, 
                        content_list, 
                        filename, 
                        start_counter + len(chunks)
                    )
                    chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
            
            # Check if we have enough content for a chunk
            if current_length >= self.chunk_size:
                # Look ahead to find a good breaking point
                if i < len(sentences) - 1:
                    # Check semantic similarity with next sentence
                    if self._should_break_here(current_chunk, sentences[i + 1]):
                        chunk_text = " ".join(current_chunk)
                        if len(chunk_text) >= self.min_chunk_size:
                            chunk = self._create_text_chunk(
                                chunk_text, 
                                page_num, 
                                content_list, 
                                filename, 
                                start_counter + len(chunks)
                            )
                            chunks.append(chunk)
                        
                        # Start new chunk with overlap
                        overlap_sentences = self._get_overlap_sentences(current_chunk)
                        current_chunk = overlap_sentences
                        current_length = sum(len(s) for s in current_chunk)
        
        # Handle remaining sentences
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunk = self._create_text_chunk(
                    chunk_text, 
                    page_num, 
                    content_list, 
                    filename, 
                    start_counter + len(chunks)
                )
                chunks.append(chunk)
        
        return chunks
    
    def _should_break_here(self, current_chunk: List[str], next_sentence: str) -> bool:
        """Determine if we should break the chunk at this point"""
        if len(current_chunk) < 2:
            return False
        
        # Get last few sentences for context
        recent_context = " ".join(current_chunk[-2:])
        
        # Check semantic similarity
        try:
            embeddings = self.embedding_model.encode([recent_context, next_sentence])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            # Break if similarity is below threshold (topic change)
            return similarity < self.similarity_threshold
        except Exception:
            # Fallback to simple heuristics
            return self._heuristic_break_check(current_chunk, next_sentence)
    
    def _heuristic_break_check(self, current_chunk: List[str], next_sentence: str) -> bool:
        """Fallback heuristic for breaking chunks"""
        # Break on paragraph boundaries
        if next_sentence.startswith(('1.', '2.', '3.', '4.', '5.', 'Chapter', 'Section')):
            return True
        
        # Break on topic indicators
        topic_indicators = ['However', 'Furthermore', 'In conclusion', 'Moreover', 
                          'On the other hand', 'In contrast', 'Similarly']
        if any(next_sentence.startswith(indicator) for indicator in topic_indicators):
            return True
        
        return False
    
    def _get_overlap_sentences(self, chunk: List[str]) -> List[str]:
        """Get sentences for overlap with next chunk"""
        if not chunk:
            return []
        
        # Calculate overlap based on character count
        total_chars = sum(len(s) for s in chunk)
        target_overlap = min(self.chunk_overlap, total_chars // 2)
        
        overlap_sentences = []
        overlap_chars = 0
        
        for sentence in reversed(chunk):
            if overlap_chars + len(sentence) <= target_overlap:
                overlap_sentences.insert(0, sentence)
                overlap_chars += len(sentence)
            else:
                break
        
        return overlap_sentences
    
    def _create_text_chunk(self, text: str, page_num: int, content_list: List[Dict], 
                          filename: str, chunk_id: int) -> SemanticChunk:
        """Create a SemanticChunk object for text content"""
        # Get bbox information from source content
        bbox_info = [content['bbox'] for content in content_list]
        
        return SemanticChunk(
            chunk_id=f"{filename}_text_{chunk_id:04d}",
            text=text,
            chunk_type="text",
            source_document=filename,
            page_numbers=[page_num],
            bbox_info=bbox_info,
            metadata={
                'chunk_method': 'semantic',
                'chunk_size': len(text),
                'page_number': page_num,
                'source_type': 'text_extraction'
            }
        )
    
    def _chunk_table_content(self, table_content: List[Dict], filename: str) -> List[SemanticChunk]:
        """Process table content into chunks"""
        chunks = []
        
        for i, table in enumerate(table_content):
            chunk = SemanticChunk(
                chunk_id=f"{filename}_table_{i:04d}",
                text=table['text'],
                chunk_type="table",
                source_document=filename,
                page_numbers=[table['page_number']],
                bbox_info=[table['bbox']],
                metadata={
                    'chunk_method': 'table_extraction',
                    'chunk_size': len(table['text']),
                    'page_number': table['page_number'],
                    'table_metadata': table.get('metadata', {}),
                    'source_type': 'table_extraction'
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_image_content(self, image_content: List[Dict], filename: str) -> List[SemanticChunk]:
        """Process image content into chunks"""
        chunks = []
        
        for i, image in enumerate(image_content):
            # Only create chunks for images with OCR text
            if image['text'] and len(image['text'].strip()) >= self.min_chunk_size:
                chunk = SemanticChunk(
                    chunk_id=f"{filename}_image_{i:04d}",
                    text=image['text'],
                    chunk_type="image",
                    source_document=filename,
                    page_numbers=[image['page_number']],
                    bbox_info=[image['bbox']],
                    metadata={
                        'chunk_method': 'ocr_extraction',
                        'chunk_size': len(image['text']),
                        'page_number': image['page_number'],
                        'image_metadata': image.get('metadata', {}),
                        'source_type': 'image_ocr'
                    }
                )
                chunks.append(chunk)
        
        return chunks
    
    def _generate_embeddings(self, chunks: List[SemanticChunk]):
        """Generate embeddings for all chunks"""
        if not chunks:
            return
        
        logger.info("Generating embeddings...")
        texts = [chunk.text for chunk in chunks]
        
        # Generate embeddings in batches
        batch_size = self.config.get('embeddings', {}).get('batch_size', settings.EMBEDDING_BATCH_SIZE)
        embeddings = self.embedding_model.encode(
            texts, 
            batch_size=batch_size,
            show_progress_bar=True
        )
        
        # Assign embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
    
    def _save_chunks(self, chunks: List[SemanticChunk]):
        """Save chunks to JSON file"""
        output_file = self.output_dir / "semantic_chunks.json"
        
        chunks_data = {
            'total_chunks': len(chunks),
            'chunk_types': {
                'text': len([c for c in chunks if c.chunk_type == 'text']),
                'table': len([c for c in chunks if c.chunk_type == 'table']),
                'image': len([c for c in chunks if c.chunk_type == 'image'])
            },
            'chunks': [chunk.to_dict() for chunk in chunks]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(chunks)} chunks to {output_file}")
        
        # Also save a summary
        summary_file = self.output_dir / "chunking_summary.json"
        summary = {
            'total_chunks': len(chunks),
            'average_chunk_size': np.mean([len(chunk.text) for chunk in chunks]),
            'chunk_size_distribution': {
                'min': min(len(chunk.text) for chunk in chunks),
                'max': max(len(chunk.text) for chunk in chunks),
                'median': np.median([len(chunk.text) for chunk in chunks])
            },
            'chunk_types': chunks_data['chunk_types'],
            'documents_processed': list(set(chunk.source_document for chunk in chunks))
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Saved chunking summary to {summary_file}")


# Example usage and testing
if __name__ == "__main__":
    # Test configuration
    config = {
        'chunk_size': settings.CHUNK_SIZE,
        'chunk_overlap': settings.CHUNK_OVERLAP,
        'min_chunk_size': settings.MIN_CHUNK_SIZE,
        'max_chunk_size': settings.MAX_CHUNK_SIZE,
        'similarity_threshold': settings.CHUNK_SIMILARITY_THRESHOLD,
        'embeddings': {
            'model_name': settings.EMBEDDING_MODEL,
            'batch_size': settings.EMBEDDING_BATCH_SIZE
        }
    }
    
    # Load processed documents
    results_file = Path(settings.PROCESSED_DATA_DIR) / "processing_results.json"
    if results_file.exists():
        with open(results_file, 'r') as f:
            processing_results = json.load(f)
        
        chunker = SemanticChunker(config)
        chunks = chunker.process_documents(processing_results['documents'])
        
        print(f"Created {len(chunks)} semantic chunks")
        print(f"Chunk types: {set(chunk.chunk_type for chunk in chunks)}")
    else:
        print("No processing results found. Run PDF processor first.")
