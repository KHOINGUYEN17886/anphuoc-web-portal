import os

# Increase worker timeout to 120 seconds to prevent HTTP 502 Bad Gateway on large report generation
timeout = 120
workers = int(os.environ.get('WEB_CONCURRENCY', 2))
keepalive = 5
