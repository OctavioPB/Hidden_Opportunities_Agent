FROM python:3.11-slim

WORKDIR /app

# System deps for torch/transformers (Sprint 6) and reportlab (Sprint 7)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Ensure data dirs exist inside the container
RUN mkdir -p data/db data/synthetic data/exports logs

# Default: run the seed script then launch the Streamlit UI
CMD ["bash", "-c", "python scripts/seed_db.py && streamlit run src/ui/app.py --server.port=8501 --server.address=0.0.0.0"]

EXPOSE 8501
