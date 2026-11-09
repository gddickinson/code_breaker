"""Start the app at http://127.0.0.1:8000 (local only)."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("codebreaker.web.app:app", host="127.0.0.1", port=8000)
