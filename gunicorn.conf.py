def post_worker_init(worker):
    from appstore.cache import start
    start()
