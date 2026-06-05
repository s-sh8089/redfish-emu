FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /data
EXPOSE 8008
ENV FLASK_APP=app
ENV FLASK_ENV=development
ENV DB_PATH=/data/redfish.db
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8008"]
