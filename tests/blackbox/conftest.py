import asyncio
import json
from dataclasses import dataclass

from pytest_asyncio import fixture
from yellowbox.clients import docker_client as yb_docker_client
from yellowbox.extras.logstash import FakeLogstashService
from yellowbox_statsd import StatsdService


@fixture(scope="session")
def cid() -> str:
    return "test_cid"


@fixture(scope="session")
def env_name():
    return "testenv"


@fixture(scope="session")
def logstash(env_vars):
    with FakeLogstashService().start() as ls:
        yield ls


@fixture(scope="session")
def docker_client():
    with yb_docker_client() as client:
        yield client


@fixture(scope="session")
def fake_dogstatsd(env_vars):
    with StatsdService().start() as statsd:
        env_vars.statsd_host = "127.0.0.1"
        env_vars.statsd_port = statsd.port
        yield statsd


@dataclass
class BlackboxEnv:
    env_name: str = ""
    logstash_host: str = ""
    logstash_port: str = ""

    statsd_host: str = "localhost"
    statsd_port: int = 8889

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    cid: str = ""

    @property
    def customers_configuration(self):
        return json.dumps(
            {
                self.cid: {"parent_cid": self.env_name},
                "dagoth": {"parent_cid": self.env_name},
                "elsa": {"parent_cid": self.env_name},
            }
        )

    def as_dotenv(self):
        env_dict = self.as_dict()
        env = [f"{k}={v}" for k, v in env_dict.items()]
        env.extend(
            [
                "PYTHONOPTIMIZE=",
                "PYTHONUNBUFFERED=1",
            ]
        )
        return env

    def as_dict(self):
        env = {
            "EnvironmentName": self.env_name,
            "role_name": "azuretests",
            "LogConnectionString": self.logstash_host,
            "LogPort": str(self.logstash_port),
            "LogHandlerType": "TCP",
            "WriteToStdout": "True",
            "StatsdConnectionString": self.statsd_host,
            "StatsdPort": str(self.statsd_port),
            "LogLevel": 10,
            "ROOKOUT_DEBUGGING_ENABLED": "false",
            "PERIODIC_CFG_UPDATE": "1",
            "send_info_log_frequency": "1",
            "METRIC_SEND_EVERY_OVERRIDE": "1",
            "VAULT_NAME": "dev",
            "ConfigurationRedisConnectionString": self.redis_host,
            "ConfigurationRedisPort": str(self.redis_port),
            "ConfigurationRedisPassword": self.redis_password,
            "CustomersConfiguration": self.customers_configuration,
        }

        return env


@fixture(scope="session")
def env_vars(env_name) -> BlackboxEnv:
    return BlackboxEnv(env_name=env_name)




@fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
