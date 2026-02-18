from fastapi import FastAPI, UploadFile, File, HTTPException
from app.analyzer import analyze_c_code
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


app = FastAPI(title="C-Sentinel")
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename.endswith(".c"):
        raise HTTPException(status_code=400, detail="Only .c files allowed")

    code = await file.read()
    result = analyze_c_code(code.decode(), file.filename)
    return result
