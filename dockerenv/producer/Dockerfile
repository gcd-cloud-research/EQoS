FROM python:3.7

COPY * /
RUN mkdir /received
WORKDIR /
RUN pip install -r requirements.txt
CMD ["python", "producer.py"]
