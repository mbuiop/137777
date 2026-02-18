bind = "0.0.0.0:5000"
workers = 8
worker_class = "gevent"
worker_connections = 1000
timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
