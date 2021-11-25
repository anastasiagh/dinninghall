FROM python:3.9.0

ADD dinninghall.py .

RUN pip install requests flask

EXPOSE 3000

CMD ["python","-u","dinninghall.py" ]