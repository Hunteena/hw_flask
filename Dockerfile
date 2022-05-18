FROM python:3.8
COPY . /app
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=TRUE
ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:5000", "app:app", "--capture-output"]