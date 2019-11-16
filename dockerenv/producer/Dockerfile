FROM python:3.7

COPY Dockerfile machinestats.py producer.py requirements.txt /
RUN mkdir /received
WORKDIR /
RUN pip install -r requirements.txt
CMD ["python", "producer.py"]
