"""
Unit tests for medical content filtering
"""

import pytest
from unittest.mock import Mock, patch

class TestMedicalFilter:
    """Test medical query filtering and entity extraction"""
    
    @pytest.fixture
    def medical_terms(self):
        return [
            "blood pressure", "hypertension", "diabetes", 
            "cholesterol", "heart rate", "glucose", 
            "symptoms", "medication", "prescription"
        ]
    
    def test_is_medical_query_positive(self):
        """Test medical query detection - positive cases"""
        from medical_filter import is_medical_query
        
        medical_queries = [
            "What is my blood pressure reading?",
            "I have diabetes type 2",
            "My cholesterol levels are high",
            "What medications should I take?",
            "I'm experiencing chest pain",
            "How to lower blood sugar?",
            "Symptoms of hypertension"
        ]
        
        for query in medical_queries:
            assert is_medical_query(query) is True, f"Failed for: {query}"
    
    def test_is_medical_query_negative(self):
        """Test medical query detection - negative cases"""
        from medical_filter import is_medical_query
        
        non_medical_queries = [
            "What's the weather today?",
            "Tell me a joke",
            "What is the capital of France?",
            "How to cook pasta?",
            "Best movies of 2024"
        ]
        
        for query in non_medical_queries:
            assert is_medical_query(query) is False, f"Failed for: {query}"
    
    def test_extract_medical_entities(self):
        """Test extracting medical entities from text"""
        from medical_filter import extract_medical_entities
        
        test_cases = [
            ("BP is 120/80", ["bp", "blood pressure"]),
            ("Type 2 diabetes medication", ["diabetes", "medication"]),
            ("High cholesterol and triglycerides", ["cholesterol", "triglycerides"]),
            ("Taking Lisinopril for hypertension", ["lisinopril", "hypertension"])
        ]
        
        for query, expected_entities in test_cases:
            entities = extract_medical_entities(query)
            for entity in expected_entities:
                assert any(entity.lower() in e.lower() for e in entities)
    
    def test_sanitize_input(self):
        """Test input sanitization"""
        from medical_filter import sanitize_input
        
        malicious_inputs = [
            ("<script>alert('XSS')</script>", "alert('XSS')"),
            ("'; DROP TABLE users; --", "DROP TABLE users"),
            ("<img src=x onerror=alert(1)>", "img src=x onerror=alert(1)")
        ]
        
        for malicious, expected_part in malicious_inputs:
            sanitized = sanitize_input(malicious)
            assert "<script>" not in sanitized
            assert "DROP TABLE" not in sanitized.upper()
    
    def test_filter_sensitive_info(self):
        """Test filtering sensitive medical information"""
        from medical_filter import filter_sensitive_info
        
        sensitive_text = "Patient SSN: 123-45-6789, DOB: 01/15/1980"
        filtered = filter_sensitive_info(sensitive_text)
        
        assert "XXX" in filtered or "***" in filtered
        assert "123-45-6789" not in filtered
    
    def test_validate_medical_query_length(self):
        """Test medical query length validation"""
        from medical_filter import validate_query_length
        
        short_query = "BP?"
        long_query = "A" * 1000
        
        assert validate_query_length(short_query) is False  # Too short
        assert validate_query_length("Normal length query") is True
        assert validate_query_length(long_query) is False  # Too long
    
    def test_categorize_medical_intent(self):
        """Test medical intent categorization"""
        from medical_filter import categorize_intent
        
        test_queries = {
            "diagnosis": ["What disease do I have?", "Am I sick?"],
            "medication": ["What pills should I take?", "Medicine dosage"],
            "symptom": ["I have a headache", "Feeling dizzy"],
            "treatment": ["How to cure this?", "Treatment options"]
        }
        
        for intent, queries in test_queries.items():
            for query in queries:
                detected_intent = categorize_intent(query)
                assert detected_intent == intent or detected_intent in intent
    
    def test_medical_term_weight(self):
        """Test medical term weighting"""
        from medical_filter import calculate_medical_relevance
        
        high_relevance = "I have severe chest pain and difficulty breathing"
        low_relevance = "What is the weather like today?"
        
        high_score = calculate_medical_relevance(high_relevance)
        low_score = calculate_medical_relevance(low_relevance)
        
        assert high_score > 0.7
        assert low_score < 0.3
    
    @patch('medical_filter.nlp_model')
    def test_ner_extraction(self, mock_nlp):
        """Test Named Entity Recognition for medical terms"""
        from medical_filter import extract_medical_ner
        
        mock_doc = Mock()
        mock_doc.ents = [Mock(label_="MEDICAL_CONDITION", text="diabetes")]
        mock_nlp.return_value = mock_doc
        
        entities = extract_medical_ner("I have diabetes")
        
        assert len(entities) > 0
