FROM python:3.7

RUN mkdir /received
WORKDIR /
COPY requirements.txt /
RUN pip install -r requirements.txt
COPY producer.py /
CMD ["python", "producer.py"]
