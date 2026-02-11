import json
import os
import sys
import tempfile
from threading import Thread
from time import time

import requests
from pytest import fixture
from python_on_whales import docker as pow_docker
from tenacity import retry, stop_after_attempt, wait_fixed
from yellowbox import connect, temp_network

SERVICE_PORT = 80
IMAGE_TAG = "biocatchtest/azuretestsservice:testing"


@fixture(scope="session")
def base_url():
    return f"http://localhost:{SERVICE_PORT}"


@fixture(scope="session")
def azuretestsservice(docker_client, env_name, env_vars, logstash):
    username = os.getenv("ART_USER")
    password = os.getenv("ART_PASS")
    # Create temporary secret files for BuildKit secrets
    with (
        tempfile.NamedTemporaryFile(mode="w", delete=False) as art_user_file,
        tempfile.NamedTemporaryFile(mode="w", delete=False) as art_pass_file,
    ):
        art_user_file.write(username)
        art_pass_file.write(password)

        art_user_path = art_user_file.name
        art_pass_path = art_pass_file.name

    try:
        pow_docker.buildx.build(
            context_path=".",
            tags=IMAGE_TAG,
            secrets=[
                f"id=art_user,src={art_user_path}",
                f"id=art_pass,src={art_pass_path}",
            ],
        )

    finally:
        os.unlink(art_user_path)
        os.unlink(art_pass_path)

    with (
        temp_network(docker_client) as network,
    ):
        env_vars.logstash_host = logstash.container_host
        env_vars.logstash_port = logstash.port

        env = env_vars.as_dotenv()

        container = docker_client.containers.run(
            IMAGE_TAG, ports={SERVICE_PORT: SERVICE_PORT}, environment=env, detach=True
        )
        container.start()

        with connect(network, container):
            log_stream = container.logs(stream=True)

            def pipe():
                nonlocal log_stream
                for line_b in log_stream:
                    line = str(line_b, "utf-8").strip()
                    print(line, file=sys.stderr)

            pipe_thread = Thread(target=pipe)
            pipe_thread.start()

            @retry(stop=stop_after_attempt(10), wait=wait_fixed(3))
            def check_health():
                response = requests.get(f"http://localhost:{SERVICE_PORT}/api/v1/health", timeout=5)
                response.raise_for_status()
                return response

            check_health()

            yield container
        container.kill("SIGKILL")
        container.remove()
