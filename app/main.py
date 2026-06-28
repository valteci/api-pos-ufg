from fastapi import FastAPI

app = FastAPI(
    title="Trabalho Final API",
    version="0.1.0",
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "API base em execucao"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
