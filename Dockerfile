FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python database_schema.py && python populate_sample_data.py

EXPOSE 10000

CMD ["python", "bot.py"]
