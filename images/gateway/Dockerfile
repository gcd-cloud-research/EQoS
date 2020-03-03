FROM python:3.7

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY gateway.py /
CMD ["gunicorn", "gateway:api", "-b", "0.0.0.0:8000"]