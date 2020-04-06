FROM python:3.7

WORKDIR /
ENV PYTHONPATH '/usr/local/lib/python3.7/site-packages'
COPY requirements.txt /
RUN pip install -r requirements.txt
RUN echo "{}" > reports.json

COPY *.py /
CMD ["python", "monitor.py"]