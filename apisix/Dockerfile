FROM apache/apisix:3.2.0-debian

# Copy configuration files
COPY config.yaml /usr/local/apisix/conf/config.yaml
COPY apisix.yaml /usr/local/apisix/conf/apisix.yaml

# Set permissions
RUN chmod 644 /usr/local/apisix/conf/config.yaml /usr/local/apisix/conf/apisix.yaml
