"""
Unit tests for RAG pipeline
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import numpy as np

class TestRAGPipeline:
    """Test Retrieval-Augmented Generation pipeline"""
    
    @pytest.fixture
    def mock_embeddings(self):
        with patch('rag_pipeline.get_embeddings') as mock:
            mock.return_value = np.random.rand(384)
            yield mock
    
    @pytest.fixture
    def sample_documents(self):
        return [
            {"id": "doc1", "content": "Blood pressure should be below 120/80", "metadata": {"source": "guide"}},
            {"id": "doc2", "content": "Diabetes patients need to monitor blood sugar", "metadata": {"source": "handbook"}},
            {"id": "doc3", "content": "Regular exercise reduces heart disease risk", "metadata": {"source": "article"}}
        ]
    
    @patch('rag_pipeline.vector_store')
    def test_index_documents(self, mock_store, sample_documents):
        """Test document indexing"""
        from rag_pipeline import index_documents
        
        mock_store.add_documents.return_value = ["doc1", "doc2", "doc3"]
        
        doc_ids = index_documents(sample_documents)
        
        assert len(doc_ids) == 3
        mock_store.add_documents.assert_called_once()
    
    @patch('rag_pipeline.vector_store')
    def test_retrieve_relevant_docs(self, mock_store):
        """Test document retrieval"""
        from rag_pipeline import retrieve_documents
        
        mock_store.similarity_search.return_value = [
            {"content": "Relevant doc 1", "score": 0.95},
            {"content": "Relevant doc 2", "score": 0.87}
        ]
        
        docs = retrieve_documents("blood pressure", k=2)
        
        assert len(docs) == 2
        assert docs[0]['score'] > docs[1]['score']
    
    @patch('rag_pipeline.llm')
    def test_generate_response(self, mock_llm):
        """Test response generation"""
        from rag_pipeline import generate_response
        
        mock_llm.generate.return_value = "Based on medical guidelines, normal blood pressure is below 120/80"
        
        context = "Medical guidelines: BP < 120/80"
        query = "What is normal blood pressure?"
        
        response = generate_response(query, context)
        
        assert "120/80" in response
        mock_llm.generate.assert_called_once()
    
    @patch('rag_pipeline.vector_store')
    @patch('rag_pipeline.llm')
    def test_full_pipeline(self, mock_llm, mock_store):
        """Test complete RAG pipeline"""
        from rag_pipeline import process_query
        
        mock_store.similarity_search.return_value = [
            {"content": "Normal BP is below 120/80", "score": 0.95}
        ]
        mock_llm.generate.return_value = "Normal blood pressure is below 120/80 mmHg"
        
        result = process_query("What is normal blood pressure?")
        
        assert result['answer'] is not None
        assert result['confidence'] > 0
        assert 'sources' in result
    
    def test_chunk_documents(self):
        """Test document chunking"""
        from rag_pipeline import chunk_document
        
        long_doc = "This is a very long document. " * 100
        chunks = chunk_document(long_doc, chunk_size=100, overlap=20)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 120 for chunk in chunks)  # With overlap
    
    @patch('rag_pipeline.vector_store')
    def test_delete_documents(self, mock_store):
        """Test document deletion"""
        from rag_pipeline import delete_documents
        
        mock_store.delete.return_value = True
        
        result = delete_documents(["doc1", "doc2"])
        
        assert result is True
        mock_store.delete.assert_called_with(["doc1", "doc2"])
    
    def test_rerank_results(self):
        """Test result reranking"""
        from rag_pipeline import rerank_results
        
        results = [
            {"content": "doc1", "score": 0.9, "relevance": 0.5},
            {"content": "doc2", "score": 0.8, "relevance": 0.9},
            {"content": "doc3", "score": 0.7, "relevance": 0.7}
        ]
        
        reranked = rerank_results(results)
        
        # Should be sorted by combined score
        assert reranked[0]['content'] == "doc2"
    
    @patch('rag_pipeline.llm')
    def test_handle_no_results(self, mock_llm):
        """Test handling when no relevant documents found"""
        from rag_pipeline import process_query
        
        mock_llm.generate.return_value = "I don't have enough information to answer that."
        
        result = process_query("Very specific medical query with no context")
        
        assert "don't have enough information" in result['answer']
