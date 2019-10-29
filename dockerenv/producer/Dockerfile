FROM python:3.7

COPY producer.py /producer.py
COPY requirements.txt /requirements.txt
WORKDIR /
RUN pip install -r requirements.txt
CMD ["python", "-u", "producer.py"]
