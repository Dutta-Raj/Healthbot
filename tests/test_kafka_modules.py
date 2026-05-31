"""
Unit tests for Kafka messaging modules
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

class TestKafkaModules:
    """Test Kafka producer and consumer"""
    
    @pytest.fixture
    def sample_message(self):
        return {
            "id": "msg_123",
            "type": "chat_request",
            "user_id": "user_456",
            "query": "What is my blood pressure?",
            "timestamp": datetime.now().isoformat()
        }
    
    @patch('kafka_producer.KafkaProducer')
    def test_producer_initialization(self, MockProducer):
        """Test Kafka producer initialization"""
        from kafka_producer import create_producer
        
        mock_producer = MockProducer.return_value
        producer = create_producer()
        
        assert producer is not None
        MockProducer.assert_called_once()
    
    @patch('kafka_producer.KafkaProducer')
    def test_send_message(self, MockProducer, sample_message):
        """Test sending message to Kafka"""
        from kafka_producer import send_message
        
        mock_producer = MockProducer.return_value
        mock_future = Mock()
        mock_future.get.return_value = Mock(topic='test_topic', partition=0, offset=123)
        mock_producer.send.return_value = mock_future
        
        result = send_message('test_topic', sample_message)
        
        assert result['offset'] == 123
        mock_producer.send.assert_called_once()
    
    @patch('kafka_producer.KafkaProducer')
    def test_send_batch_messages(self, MockProducer, sample_message):
        """Test sending batch messages"""
        from kafka_producer import send_batch
        
        mock_producer = MockProducer.return_value
        messages = [sample_message] * 5
        
        results = send_batch('test_topic', messages)
        
        assert len(results) == 5
        assert mock_producer.send.call_count == 5
    
    @patch('kafka_consumer.KafkaConsumer')
    def test_consumer_initialization(self, MockConsumer):
        """Test Kafka consumer initialization"""
        from kafka_consumer import create_consumer
        
        mock_consumer = MockConsumer.return_value
        consumer = create_consumer('test_topic')
        
        assert consumer is not None
        MockConsumer.assert_called_once()
    
    @patch('kafka_consumer.KafkaConsumer')
    def test_consume_messages(self, MockConsumer, sample_message):
        """Test consuming messages from Kafka"""
        from kafka_consumer import consume_messages
        
        mock_consumer = MockConsumer.return_value
        mock_msg = Mock()
        mock_msg.value = json.dumps(sample_message).encode()
        mock_consumer.__iter__.return_value = [mock_msg]
        
        messages = list(consume_messages('test_topic', timeout_seconds=1))
        
        assert len(messages) == 1
        assert messages[0]['id'] == sample_message['id']
    
    def test_message_serialization(self):
        """Test message serialization/deserialization"""
        from kafka_config import serialize_message, deserialize_message
        
        original_msg = {"key": "value", "number": 123}
        serialized = serialize_message(original_msg)
        deserialized = deserialize_message(serialized)
        
        assert deserialized == original_msg
    
    def test_message_validation(self):
        """Test message schema validation"""
        from kafka_config import validate_message
        
        valid_msg = {
            "id": "123",
            "type": "chat",
            "timestamp": datetime.now().isoformat()
        }
        
        invalid_msg = {"missing": "fields"}
        
        assert validate_message(valid_msg) is True
        assert validate_message(invalid_msg) is False
    
    @patch('kafka_consumer.KafkaConsumer')
    def test_error_handling(self, MockConsumer):
        """Test error handling in consumer"""
        from kafka_consumer import consume_messages
        
        mock_consumer = MockConsumer.return_value
        mock_consumer.__iter__.side_effect = Exception("Connection error")
        
        with pytest.raises(Exception):
            list(consume_messages('test_topic'))
