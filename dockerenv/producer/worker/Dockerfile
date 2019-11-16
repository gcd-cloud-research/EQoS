FROM python:3.7

COPY *.py /
COPY *.txt /
WORKDIR /
RUN pip install -r requirements.txt
CMD ["python", "wrapper.py"]
