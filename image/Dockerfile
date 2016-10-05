FROM python:2.7
MAINTAINER Diego Diaz <diego@dedosmedia.com>

ADD ./app /app
WORKDIR /app/

RUN pip install -r requirements.txt
RUN ["chmod", "+x", "./monitor.py"]

CMD ["python","./monitor.py"]

EXPOSE 4999