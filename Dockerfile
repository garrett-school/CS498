FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir openai python-dotenv

COPY . .

CMD ["python", "AbstractionLayers.py"]
