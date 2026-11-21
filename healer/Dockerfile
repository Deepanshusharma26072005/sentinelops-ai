FROM python:3.12-slim
WORKDIR /healer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY healer.py .
CMD ["python", "healer.py"]