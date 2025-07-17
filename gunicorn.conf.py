bind = "0.0.0.0:10000"
workers = 1
timeout = 600  # 增加到10分钟，支持大文件处理
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
preload_app = True