sktop\Chatbot\app.py", line 461
    })a
      ^
SyntaxError: invalid syntax

C:\Users\KIIT\Desktop\Chatbot>python app.py
ℹ️ Kafka is disabled - running in local mode
✅ MongoDB connected successfully.
✅ Hugging Face API connected successfully. Welcome Dutta-Raj!
✅ Token has READ permissions - perfect for inference!
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://10.5.67.189:5000
Press CTRL+C to quit
 * Restarting with watchdog (windowsapi)
ℹ️ Kafka is disabled - running in local mode
✅ MongoDB connected successfully.
✅ Hugging Face API connected successfully. Welcome Dutta-Raj!
✅ Token has READ permissions - perfect for inference!
 * Debugger is active!
 * Debugger PIN: 415-946-912
127.0.0.1 - - [25/Oct/2025 18:29:25] "POST /login HTTP/1.1" 200 -
Hugging Face API error: 404
127.0.0.1 - - [25/Oct/2025 18:29:27] "POST /chat HTTP/1.1" 200 -
Hugging Face API error: 404
ℹ️ [KAFKA-LOG] Would send to health-critical-alerts: {'user_id': '68fcc880cd8338750545e4eb', 'alert_type': 'CRITICAL_KEYWORD_DETECTED', 'keywords': ['chest pain'], 'user_message': "I have severe chest pain and can't breathe properly", 'bot_response': "Don't skip breakfast! A balanced morning meal can help maintain energy levels throughout the day.\n\n🍎 Remember: A registered dietitian can provide personalized nutrition advice.", 'timestamp': '2025-10-25T18:29:30.218863', 'severity': 'HIGH'}
🚨 CRITICAL ALERT DETECTED: ['chest pain']
127.0.0.1 - - [25/Oct/2025 18:29:30] "POST /chat HTTP/1.1" 200 -

