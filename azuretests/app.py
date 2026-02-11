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

    async def shutdown(self):
        tasks = [self.metrics.close()]
        try:
            await wait_for(gather(*tasks), timeout=5)
        except TimeoutError:
            logger.error("closing tasks did not finish in a timely manner!")
        logging.shutdown()
