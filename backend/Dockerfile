FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    verilator \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install CPU-only PyTorch before everything else — avoids pulling the
# massive CUDA build (~2GB) that sentence-transformers would otherwise fetch
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
