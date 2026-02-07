"""Allow ``python -m search`` to start the API server."""

import os
import uvicorn

# Prevent OpenMP crash on macOS when FAISS + other libs both link libomp
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

if __name__ == "__main__":
    uvicorn.run("search.api:app", host="0.0.0.0", port=8000, reload=True)
