FROM python:3.9

RUN pip install requests==2.22.0
RUN pip install jsonpath_ng==1.5.3
RUN useradd -r -s /bin/false 10001
COPY . /opt/data-extraction
RUN chown -R 10001:10001 /opt/data-extraction
WORKDIR /opt/data-extraction

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER 10001

ENTRYPOINT ["docker-entrypoint.sh"]