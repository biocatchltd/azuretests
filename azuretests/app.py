import logging
from asyncio import gather, wait_for
from logging import getLogger
from typing import Any
from azuretests import __version__


from backendcommon.health_data import HealthData

from bc_logging.settings import logging_settings_ev, setup_logging
from bc_metrics import MetricCollector
from fastapi import FastAPI

from azuretests.env_vars import env_name_ev, metric_send_every_override_ev
from azuretests.loader import start_load
from env_vars import  azure_share_name_ev, connection_string_ev

from env_vars import azure_share_name_ev
from azure.storage.fileshare.aio import ShareServiceClient


logger = getLogger("biocatch." + __name__)


class AzureTestsService(FastAPI):
    metrics: MetricCollector

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.env_name = env_name_ev.get()
        self.health_data = HealthData({"version": __version__, "environment": self.env_name})

    async def startup(self):
        self.metrics = MetricCollector.from_env()
        await self.metrics.connect(metric_send_every_override_ev.get())

        logging_settings = logging_settings_ev.get(
            server_version=__version__,
            asyncio_logging=False,
        )
        setup_logging(logging_settings)
        self.metrics = MetricCollector.from_env()
        await self.metrics.connect(metric_send_every_override_ev.get())
        connection_string = connection_string_ev.get()
        service_client = ShareServiceClient.from_connection_string(connection_string)
        share_name = azure_share_name_ev.get()
        directory_name = "load_tests"

        print("calling get_share_client")
        share_client = service_client.get_share_client(share_name)
        print("called get_share_client")

        dir_client = share_client.get_directory_client(directory_name)


        await start_load(dir_client, self.metrics)

    async def shutdown(self):
        tasks = [self.metrics.close()]
        try:
            await wait_for(gather(*tasks), timeout=5)
        except TimeoutError:
            logger.error("closing tasks did not finish in a timely manner!")
        logging.shutdown()

