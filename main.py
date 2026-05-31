from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
import uvicorn

app = FastAPI(title="MediBot AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve index.html at root
@app.get("/")
async def serve_frontend():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Frontend not found"}

# Also serve static files
if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/health")
async def health():
    return {"status": "healthy", "database": "MongoDB Atlas"}

# Auth endpoints would be here (they are in your main.py)
# For now, just serving frontend

if __name__ == "__main__":
    print("🏥 MediBot AI Running...")
    uvicorn.run(app, host="0.0.0.0", port=10000)
