FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN mkdir -p /app/data
EXPOSE 8501
CMD sh -c 'streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}'
