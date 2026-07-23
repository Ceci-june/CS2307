import sys
from hypercorn.config import Config
from hypercorn.run import run
from server import app
from dotenv import dotenv_values

env_config = dotenv_values('.env')


def hypercorn_server():
    host = env_config.get('SERVER_HOST', '0.0.0.0')
    port = env_config.get('SERVER_PORT', 5988)
    print(f"Server running on {host}:{port}")
    config = Config()
    config.bind = [f"{host}:{port}"]
    config.loglevel = "INFO"
    config.workers = int(env_config.get('BACKEND_WORKER', 2))
    config.worker_class = "asyncio"
    config.max_app_queue_size = 20
    config.application_path = 'server:app'
    config.use_reloader = False
    config.accesslog = "logs/access.log"
    run(config)


if __name__ == '__main__':
    sys.exit(hypercorn_server())
