"""
Reranking Module for RAG Evaluation
Implements BM25 and MMR (Maximal Marginal Relevance) reranking algorithms
"""

import logging
import json
import math
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from collections import Counter

logger = logging.getLogger(__name__)


class BM25Reranker:
    """
    BM25 (Best Matching 25) reranking implementation
    """
    
    def __init__(self, k1: float = 1.2, b: float = 0.75):
        """
        Initialize BM25 with parameters
        
        Args:
            k1: Controls term frequency saturation (typically 1.2-2.0)
            b: Controls field length normalization (typically 0.75)
        """
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.idf_scores = {}
        self.vocabulary = set()
        
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization and preprocessing"""
        # Convert to lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
        return tokens
    
    def fit(self, corpus: List[str]):
        """
        Fit BM25 on a corpus of documents
        
        Args:
            corpus: List of document texts
        """
        self.corpus = corpus
        tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        
        # Calculate document lengths
        self.doc_lengths = [len(doc) for doc in tokenized_corpus]
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0
        
        # Build vocabulary
        self.vocabulary = set()
        for doc in tokenized_corpus:
            self.vocabulary.update(doc)
        
        # Calculate IDF scores
        N = len(corpus)
        for term in self.vocabulary:
            # Count documents containing the term
            doc_count = sum(1 for doc in tokenized_corpus if term in doc)
            # IDF = log((N - doc_count + 0.5) / (doc_count + 0.5))
            self.idf_scores[term] = math.log((N - doc_count + 0.5) / (doc_count + 0.5))
    
    def score(self, query: str, doc_idx: int) -> float:
        """
        Calculate BM25 score for a query-document pair
        
        Args:
            query: Query text
            doc_idx: Document index in corpus
            
        Returns:
            BM25 score
        """
        if doc_idx >= len(self.corpus):
            return 0.0
        
        query_terms = self._tokenize(query)
        doc_terms = self._tokenize(self.corpus[doc_idx])
        doc_length = self.doc_lengths[doc_idx]
        
        # Count term frequencies in document
        term_counts = Counter(doc_terms)
        
        score = 0.0
        for term in query_terms:
            if term in self.vocabulary:
                # Term frequency in document
                tf = term_counts.get(term, 0)
                
                # BM25 formula
                idf = self.idf_scores.get(term, 0)
                tf_component = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length)))
                score += idf * tf_component
        
        return score
    
    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Rerank documents using BM25 scores
        
        Args:
            query: Search query
            documents: List of document dictionaries with 'text' field
            top_k: Number of top documents to return
            
        Returns:
            Reranked list of documents with BM25 scores
        """
        # Extract texts and fit BM25 if needed
        texts = [doc.get('text', '') for doc in documents]
        if not self.corpus or len(self.corpus) != len(texts):
            self.fit(texts)
        
        # Calculate BM25 scores
        scored_docs = []
        for i, doc in enumerate(documents):
            bm25_score = self.score(query, i)
            doc_copy = doc.copy()
            doc_copy['bm25_score'] = bm25_score
            doc_copy['original_rank'] = doc.get('rank', i + 1)
            scored_docs.append(doc_copy)
        
        # Sort by BM25 score (descending)
        reranked = sorted(scored_docs, key=lambda x: x['bm25_score'], reverse=True)
        
        # Update ranks and return top_k
        for i, doc in enumerate(reranked[:top_k]):
            doc['reranked_position'] = i + 1
        
        return reranked[:top_k]


class MMRReranker:
    """
    MMR (Maximal Marginal Relevance) reranking implementation
    Balances relevance and diversity
    """
    
    def __init__(self, lambda_param: float = 0.5):
        """
        Initialize MMR with lambda parameter
        
        Args:
            lambda_param: Balance between relevance (1.0) and diversity (0.0)
        """
        self.lambda_param = lambda_param
        
    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for texts (simplified - could use sentence-transformers)"""
        # For now, use simple TF-IDF vectors
        vectorizer = CountVectorizer(max_features=1000, stop_words='english')
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
            return tfidf_matrix.toarray()
        except:
            # Fallback to random vectors if texts are empty
            return np.random.rand(len(texts), 100)
    
    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Rerank documents using MMR algorithm
        
        Args:
            query: Search query
            documents: List of document dictionaries
            top_k: Number of documents to return
            
        Returns:
            Reranked list with MMR scores
        """
        if not documents:
            return []
        
        # Extract texts
        doc_texts = [doc.get('text', '') for doc in documents]
        all_texts = [query] + doc_texts
        
        # Get embeddings
        embeddings = self._get_embeddings(all_texts)
        query_embedding = embeddings[0]
        doc_embeddings = embeddings[1:]
        
        # Calculate relevance scores (cosine similarity with query)
        relevance_scores = cosine_similarity([query_embedding], doc_embeddings)[0]
        
        # MMR algorithm
        selected = []
        remaining_indices = list(range(len(documents)))
        
        while len(selected) < top_k and remaining_indices:
            mmr_scores = []
            
            for idx in remaining_indices:
                # Relevance score
                relevance = relevance_scores[idx]
                
                # Diversity score (max similarity with already selected)
                if not selected:
                    diversity = 0
                else:
                    selected_embeddings = [doc_embeddings[i] for i in selected]
                    similarities = cosine_similarity([doc_embeddings[idx]], selected_embeddings)[0]
                    diversity = max(similarities) if similarities.size > 0 else 0
                
                # MMR score
                mmr_score = self.lambda_param * relevance - (1 - self.lambda_param) * diversity
                mmr_scores.append((idx, mmr_score))
            
            # Select document with highest MMR score
            best_idx, best_score = max(mmr_scores, key=lambda x: x[1])
            selected.append(best_idx)
            remaining_indices.remove(best_idx)
        
        # Create reranked results
        reranked = []
        for i, doc_idx in enumerate(selected):
            doc_copy = documents[doc_idx].copy()
            doc_copy['mmr_score'] = relevance_scores[doc_idx]
            doc_copy['original_rank'] = documents[doc_idx].get('rank', doc_idx + 1)
            doc_copy['reranked_position'] = i + 1
            reranked.append(doc_copy)
        
        return reranked


class RerankerComparison:
    """
    Comparison framework for different reranking methods
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bm25_config = config.get('bm25', {})
        self.mmr_config = config.get('mmr', {})
        
        # Initialize rerankers
        self.bm25_reranker = BM25Reranker(
            k1=self.bm25_config.get('k1', 1.2),
            b=self.bm25_config.get('b', 0.75)
        )
        
        self.mmr_reranker = MMRReranker(
            lambda_param=self.mmr_config.get('lambda_param', 0.5)
        )
        
        # Setup results directory
        self.results_dir = Path("data/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("RerankerComparison initialized")
    
    def compare_methods(self, benchmark_results: Dict[str, Any], 
                       methods: List[str] = None) -> Dict[str, Any]:
        """
        Compare reranking methods on benchmark results
        
        Args:
            benchmark_results: Results from benchmark runner
            methods: List of methods to compare ['bm25', 'mmr']
            
        Returns:
            Comparison results
        """
        methods = methods or ['bm25', 'mmr']
        
        logger.info(f"Comparing reranking methods: {methods}")
        
        comparison_results = {
            'metadata': {
                'methods': methods,
                'reranking_config': self.config
            },
            'results': {},
            'summary': {}
        }
        
        # Test queries from benchmark
        test_queries = benchmark_results['metadata']['test_queries']
        
        # Load semantic chunks for document texts
        chunks_file = Path("data/processed/semantic_chunks.json")
        with open(chunks_file, 'r') as f:
            chunks_data = json.load(f)
        all_chunks = chunks_data['chunks']
        
        # Test each database+index combination
        for db_name, db_results in benchmark_results['results'].items():
            if 'error' in db_results:
                continue
            
            comparison_results['results'][db_name] = {}
            
            for index_type, combo_results in db_results.items():
                if 'performance' not in combo_results:
                    continue
                
                logger.info(f"Testing reranking on {db_name}/{index_type}")
                
                reranking_results = {
                    'original_performance': combo_results['performance'],
                    'methods': {}
                }
                
                # Test each query
                for query_data in combo_results['queries']:
                    query_text = query_data['query_text']
                    sample_results = query_data.get('sample_results', [])
                    
                    if not sample_results:
                        continue
                    
                    # Get full document texts for reranking
                    documents_with_text = []
                    for result in sample_results:
                        chunk_id = result.get('chunk_id', '')
                        # Find full chunk data
                        chunk_data = next((c for c in all_chunks if c['chunk_id'] == chunk_id), None)
                        if chunk_data:
                            doc_with_text = result.copy()
                            doc_with_text['text'] = chunk_data['text']
                            documents_with_text.append(doc_with_text)
                    
                    if not documents_with_text:
                        continue
                    
                    # Test each reranking method
                    for method in methods:
                        if method not in reranking_results['methods']:
                            reranking_results['methods'][method] = []
                        
                        start_time = time.time()
                        
                        if method == 'bm25':
                            reranked = self.bm25_reranker.rerank(
                                query_text, 
                                documents_with_text, 
                                top_k=self.bm25_config.get('final_k', 10)
                            )
                        elif method == 'mmr':
                            reranked = self.mmr_reranker.rerank(
                                query_text, 
                                documents_with_text, 
                                top_k=self.mmr_config.get('final_k', 10)
                            )
                        else:
                            continue
                        
                        reranking_time = time.time() - start_time
                        
                        # Calculate reranking metrics
                        metrics = self._calculate_reranking_metrics(
                            documents_with_text, reranked, method
                        )
                        metrics['reranking_time'] = reranking_time
                        metrics['query'] = query_text
                        
                        reranking_results['methods'][method].append(metrics)
                
                comparison_results['results'][db_name][index_type] = reranking_results
        
        # Generate summary
        comparison_results['summary'] = self._generate_reranking_summary(comparison_results['results'])
        
        # Save results
        self._save_reranking_results(comparison_results)
        
        logger.info("Reranking comparison completed")
        return comparison_results
    
    def _calculate_reranking_metrics(self, original: List[Dict], reranked: List[Dict], 
                                   method: str) -> Dict[str, Any]:
        """Calculate metrics for reranking quality"""
        metrics = {
            'method': method,
            'original_count': len(original),
            'reranked_count': len(reranked),
            'rank_changes': 0,
            'position_improvements': 0,
            'position_degradations': 0,
            'average_rank_change': 0.0
        }
        
        if not original or not reranked:
            return metrics
        
        # Calculate rank changes
        rank_changes = []
        for reranked_doc in reranked:
            original_rank = reranked_doc.get('original_rank', 0)
            new_rank = reranked_doc.get('reranked_position', 0)
            
            if original_rank > 0 and new_rank > 0:
                change = original_rank - new_rank  # Positive = improvement
                rank_changes.append(change)
                
                if change > 0:
                    metrics['position_improvements'] += 1
                elif change < 0:
                    metrics['position_degradations'] += 1
        
        if rank_changes:
            metrics['rank_changes'] = len([c for c in rank_changes if c != 0])
            metrics['average_rank_change'] = sum(rank_changes) / len(rank_changes)
        
        # Add method-specific scores
        if method == 'bm25':
            bm25_scores = [doc.get('bm25_score', 0) for doc in reranked]
            metrics['average_bm25_score'] = sum(bm25_scores) / len(bm25_scores) if bm25_scores else 0
            metrics['max_bm25_score'] = max(bm25_scores) if bm25_scores else 0
        
        elif method == 'mmr':
            mmr_scores = [doc.get('mmr_score', 0) for doc in reranked]
            metrics['average_mmr_score'] = sum(mmr_scores) / len(mmr_scores) if mmr_scores else 0
            metrics['max_mmr_score'] = max(mmr_scores) if mmr_scores else 0
        
        return metrics
    
    def _generate_reranking_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of reranking performance"""
        summary = {
            'method_performance': {},
            'best_method_by_db': {},
            'overall_best_method': None
        }
        
        method_stats = {}
        
        for db_name, db_results in results.items():
            db_method_performance = {}
            
            for index_type, combo_results in db_results.items():
                for method, method_results in combo_results.get('methods', {}).items():
                    if method not in method_stats:
                        method_stats[method] = []
                    
                    if method not in db_method_performance:
                        db_method_performance[method] = []
                    
                    # Aggregate metrics for this method
                    for result in method_results:
                        avg_change = result.get('average_rank_change', 0)
                        method_stats[method].append(avg_change)
                        db_method_performance[method].append(avg_change)
            
            # Find best method for this database
            if db_method_performance:
                best_method = max(db_method_performance.keys(), 
                                key=lambda m: sum(db_method_performance[m]) / len(db_method_performance[m]) if db_method_performance[m] else 0)
                summary['best_method_by_db'][db_name] = best_method
        
        # Calculate overall method performance
        for method, changes in method_stats.items():
            if changes:
                summary['method_performance'][method] = {
                    'average_rank_improvement': sum(changes) / len(changes),
                    'positive_changes': len([c for c in changes if c > 0]),
                    'total_tests': len(changes),
                    'improvement_rate': len([c for c in changes if c > 0]) / len(changes)
                }
        
        # Find overall best method
        if summary['method_performance']:
            best_method = max(summary['method_performance'].keys(),
                            key=lambda m: summary['method_performance'][m]['average_rank_improvement'])
            summary['overall_best_method'] = best_method
        
        return summary
    
    def _save_reranking_results(self, results: Dict[str, Any]):
        """Save reranking comparison results"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Save full results
        results_file = self.results_dir / f"reranking_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Save latest (for easy access)
        latest_file = self.results_dir / "latest_reranking_results.json"
        with open(latest_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Reranking results saved to {results_file}")
    
    def print_summary(self, results: Dict[str, Any]):
        """Print formatted summary of reranking results"""
        summary = results.get('summary', {})
        
        print("\n" + "="*60)
        print("RERANKING COMPARISON SUMMARY")
        print("="*60)
        
        print(f"Overall best method: {summary.get('overall_best_method', 'N/A')}")
        
        print("\nMethod Performance:")
        for method, stats in summary.get('method_performance', {}).items():
            avg_improvement = stats.get('average_rank_improvement', 0)
            improvement_rate = stats.get('improvement_rate', 0) * 100
            print(f"  {method.upper()}: {avg_improvement:+.2f} avg rank change ({improvement_rate:.1f}% improved)")
        
        print("\nBest Method by Database:")
        for db_name, best_method in summary.get('best_method_by_db', {}).items():
            print(f"  {db_name.upper()}: {best_method}")


# Example usage and testing
if __name__ == "__main__":
    # Test reranking on sample documents
    config = {
        'bm25': {
            'k1': 1.2,
            'b': 0.75,
            'final_k': 10
        },
        'mmr': {
            'lambda_param': 0.5,
            'final_k': 10
        }
    }
    
    # Load latest benchmark results
    results_file = Path("data/results/latest_benchmark_results.json")
    if results_file.exists():
        with open(results_file, 'r') as f:
            benchmark_results = json.load(f)
        
        comparison = RerankerComparison(config)
        reranking_results = comparison.compare_methods(benchmark_results)
        
        comparison.print_summary(reranking_results)
    else:
        print("No benchmark results found. Run benchmarks first.")
