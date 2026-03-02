FROM python:3.11-slim

WORKDIR /app

# Kopijuojame priklausomybes ir jas diegiame
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopijuojame visą kodą
COPY . .

# Atidarome prievadą (port)
EXPOSE 8000

# Paleidimo komanda
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
