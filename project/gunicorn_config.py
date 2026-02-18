cat > gunicorn_config.py << 'EOF'
bind = "0.0.0.0:5000"
workers = 4
threads = 2
worker_class = "gthread"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
EOF
