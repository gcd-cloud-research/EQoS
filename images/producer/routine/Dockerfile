FROM python:3.7

ENV PYTHONPATH '/usr/local/lib/python3.7/site-packages'
RUN pip3 install --upgrade pip setuptools wheel
COPY requirements.txt /
RUN pip3 install -r requirements.txt

COPY *.py /
ENTRYPOINT ["python3"]