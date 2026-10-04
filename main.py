"""Start the API with:  py main.py   (or: python main.py)"""
import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "3001")),
        reload=True,  # restarts automatically when you save a file
    )
