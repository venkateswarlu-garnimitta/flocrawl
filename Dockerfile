FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
COPY src/ src/
RUN pip install -e .

ENV PORT=7860
EXPOSE 7860

CMD ["python", "-m", "flocrawl"]
