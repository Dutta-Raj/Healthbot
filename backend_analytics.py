# backend_analytics.py - Add to your main API
"""
Analytics endpoints for activity tracking
Add these to your main_api_with_queue.py
"""

from fastapi import FastAPI, Query
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict

# Add these endpoints to your existing FastAPI app

@app.get("/analytics/activity")
async def get_activity(
    range: str = Query("today", description="Time range: today, yesterday, 7days, 30days, 156days, max")
):
    """Get activity history for specified time range"""
    
    # Calculate date range
    now = datetime.utcnow()
    ranges = {
        "today": now - timedelta(days=1),
        "yesterday": now - timedelta(days=2),
        "7days": now - timedelta(days=7),
        "30days": now - timedelta(days=30),
        "156days": now - timedelta(days=156),
        "max": datetime(2020, 1, 1)
    }
    
    cutoff = ranges.get(range, ranges["today"])
    
    # Get messages from queue
    messages = message_bus.queue.get_messages('healthbot.chat.requests', 1000)
    
    # Filter by date
    filtered = []
    for msg in messages:
        msg_date = datetime.fromisoformat(msg['timestamp']) if 'timestamp' in msg else now
        if msg_date >= cutoff:
            filtered.append(msg)
    
    # Group by day for chart
    daily_data = defaultdict(int)
    for msg in filtered:
        date = datetime.fromisoformat(msg['timestamp']).strftime('%Y-%m-%d')
        daily_data[date] += 1
    
    return {
        "range": range,
        "total": len(filtered),
        "messages": filtered,
        "daily_activity": dict(daily_data),
        "timeframe": {
            "start": cutoff.isoformat(),
            "end": now.isoformat()
        }
    }

@app.get("/analytics/stats")
async def get_analytics_stats():
    """Get comprehensive analytics statistics"""
    
    # Get all messages
    requests = message_bus.queue.get_messages('healthbot.chat.requests', 10000)
    responses = message_bus.queue.get_messages('healthbot.chat.responses', 10000)
    
    # Calculate statistics
    total_chats = len(requests)
    unique_users = len(set(msg.get('data', {}).get('user_id', '') for msg in requests))
    
    # Average response length
    avg_response_length = sum(len(msg.get('data', {}).get('response', '')) for msg in responses) / max(len(responses), 1)
    
    # Activity by hour
    hourly_activity = defaultdict(int)
    for msg in requests:
        hour = datetime.fromisoformat(msg['timestamp']).hour
        hourly_activity[hour] += 1
    
    return {
        "total_chats": total_chats,
        "unique_users": unique_users,
        "total_responses": len(responses),
        "avg_response_length": int(avg_response_length),
        "hourly_activity": dict(hourly_activity),
        "queue_stats": message_bus.get_stats()
    }
