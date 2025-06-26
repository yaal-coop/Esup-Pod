#------------------------------------------------------------------------------------------------------------------------------
#  (\___/)
#  (='.'=) Dockerfile multi-stages node & python
#  (")_(")
#------------------------------------------------------------------------------------------------------------------------------
# Conteneur node
ARG PYTHON_VERSION

#------------------------------------------------------------------------------------------------------------------------------
# Conteneur python
FROM $PYTHON_VERSION
WORKDIR /tmp/pod
COPY ./pod/ .

WORKDIR /usr/src/app

COPY ./requirements.txt .
COPY ./requirements-conteneur.txt .
COPY ./requirements-encode.txt .
COPY ./requirements-dev.txt .

RUN pip3 install --no-cache-dir -r requirements-dev.txt \
    && pip3 install elasticsearch==7.17.9

COPY ./dockerfile-dev-with-volumes/pod-activitypub/my-entrypoint-activitypub.sh /tmp/my-entrypoint-activitypub.sh
RUN chmod 755 /tmp/my-entrypoint-activitypub.sh

ENTRYPOINT ["bash", "/tmp/my-entrypoint-activitypub.sh"]
