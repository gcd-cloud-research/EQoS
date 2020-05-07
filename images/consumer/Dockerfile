FROM python:3.7

RUN pip install --upgrade pip

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY consumer.py /
ENV REGISTRY "192.168.101.76:5000"

CMD ["python", "consumer.py"]