FROM python:3.7

COPY requirements.txt /
WORKDIR /
RUN pip install -r requirements.txt
COPY api.py config.json /
CMD ["gunicorn", "api:api", "-b", "0.0.0.0:8000"]
