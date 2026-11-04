FROM nginx:1.29.4-alpine

RUN apk add --no-cache python3 && rm -f /etc/nginx/conf.d/default.conf
COPY deployment/tls/nginx.conf.template /etc/nginx/nginx.conf.template
COPY deployment/tls/render_nginx_config.py /usr/local/bin/render_nginx_config.py
RUN chmod 0555 /usr/local/bin/render_nginx_config.py

CMD ["python3", "/usr/local/bin/render_nginx_config.py"]
