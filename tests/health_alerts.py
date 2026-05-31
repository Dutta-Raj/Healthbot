import re
from datetime import datetime

class AlertManager:
    def __init__(self):
        self.critical_keywords = [
            'heart attack', 'chest pain', 'stroke', 'cannot breathe', 
            'difficulty breathing', 'severe pain', 'bleeding heavily', 
            'unconscious', 'suicide', 'self harm', 'dying', 'emergency',
            'ambulance', '911', 'emergency room'
        ]
        
        self.urgent_keywords = [
            'high fever', 'broken bone', 'severe headache', 'allergic reaction',
            'burn', 'poison', 'overdose', 'severe vomiting', 'severe diarrhea'
        ]
    
    def analyze_message_for_alerts(self, user_id, user_message, bot_response):
        """Analyze messages for critical health alerts"""
        user_msg_lower = user_message.lower()
        
        # Check for critical emergencies
        critical_match = any(keyword in user_msg_lower for keyword in self.critical_keywords)
        if critical_match:
            alert_data = {
                "user_id": user_id,
                "alert_level": "CRITICAL",
                "message": user_message,
                "response": bot_response,
                "timestamp": datetime.now().isoformat(),
                "action_required": True,
                "suggested_action": "IMMEDIATE_MEDICAL_ATTENTION"
            }
            print(f"🚨 CRITICAL ALERT triggered for user {user_id}: {user_message}")
            return alert_data
        
        # Check for urgent issues
        urgent_match = any(keyword in user_msg_lower for keyword in self.urgent_keywords)
        if urgent_match:
            alert_data = {
                "user_id": user_id,
                "alert_level": "URGENT",
                "message": user_message,
                "response": bot_response,
                "timestamp": datetime.now().isoformat(),
                "action_required": True,
                "suggested_action": "SEEK_MEDICAL_ADVICE_SOON"
            }
            print(f"⚠️ URGENT ALERT triggered for user {user_id}: {user_message}")
            return alert_data
        
        return None

# Create a global instance
alert_manager = AlertManager()
