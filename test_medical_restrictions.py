# test_medical_restrictions.py
"""Test medical query restrictions"""

import unittest
from medical_rag_restricted import is_medical_query

class TestMedicalRestrictions(unittest.TestCase):
    
    def test_medical_queries(self):
        """Test that medical queries pass"""
        medical_queries = [
            "What is normal blood pressure?",
            "I have a headache",
            "How to manage diabetes?",
            "Fever treatment",
            "Heart attack symptoms"
        ]
        
        for query in medical_queries:
            is_medical, msg = is_medical_query(query)
            self.assertTrue(is_medical, f"'{query}' should be medical")
    
    def test_non_medical_queries(self):
        """Test that non-medical queries are rejected"""
        non_medical_queries = [
            "What's the weather today?",
            "Stock market news",
            "Best movie to watch",
            "How to cook pasta?",
            "Football scores"
        ]
        
        for query in non_medical_queries:
            is_medical, msg = is_medical_query(query)
            self.assertFalse(is_medical, f"'{query}' should be rejected")
            self.assertIn("medical", msg.lower())
    
    def test_kafka_enabled(self):
        """Test Kafka configuration"""
        import os
        kafka_enabled = os.getenv('KAFKA_ENABLED', 'false').lower() == 'true'
        print(f"Kafka enabled: {kafka_enabled}")

if __name__ == "__main__":
    unittest.main()
