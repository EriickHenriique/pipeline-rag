import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "fin_pipeline.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,   # Habilita o modo de recarga automática para desenvolvimento
        log_level="info",
    )