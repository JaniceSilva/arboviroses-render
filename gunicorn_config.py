# gunicorn_config.py

# Número de workers (processos)
workers = 1

# Número de threads por worker
threads = 3

# Timeout em segundos (10 minutos)
timeout = 1200

# Endereço de bind
bind = "0.0.0.0:8000"

# Logs
accesslog = "-"  # stdout
errorlog = "-"   # stdout
capture_output = True