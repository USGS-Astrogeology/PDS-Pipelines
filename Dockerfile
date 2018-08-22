# VERSION 1.9.0-4
# AUTHOR: Matthieu "Puckel_" Roisil
# DESCRIPTION: Basic Airflow container
# BUILD: docker build --rm -t puckel/docker-airflow .
# SOURCE: https://github.com/puckel/docker-airflow

FROM puckel/docker-airflow:latest
ADD . /app
RUN python -m pip install --user /app \
    && python -m pip install --user geoalchemy2
    

