FROM debian:bullseye

RUN apt-get -y update
RUN apt-get -y install python3 pip

WORKDIR swag
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt
COPY ./*.py .
COPY ./swag ./swag

#ENTRYPOINT ["python3", "wsgi.py"]
ENTRYPOINT gunicorn swag:app --bind=0.0.0.0:8080
