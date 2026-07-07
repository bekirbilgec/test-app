from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Test App", version="1.0.0")

@app.get("/health")
def health():
    return {"status": "ok", "service": "test-app"}

@app.get("/")
def root():
    return {"message": "Test App is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)