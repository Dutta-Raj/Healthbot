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

# Serve frontend files
frontend_path = os.path.join(os.path.dirname(__file__), "src/frontend")
if os.path.exists(frontend_path):
    # Mount static files
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    
    # Serve frontend at root
    @app.get("/")
    async def serve_frontend():
        index_file = os.path.join(frontend_path, "simple.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend not found"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "MediBot AI is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
