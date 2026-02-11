import logging
from contextlib import asynccontextmanager

import uvicorn
from backendcommon.webserver.helpers import enable_exception_handlers

from azuretests import __version__
from azuretests.app import AzureTestsService


logger = logging.getLogger("biocatch." + __name__)


def app() -> AzureTestsService:
    @asynccontextmanager
    async def lifespan(AzureTest: AzureTestsService):
        try:
            await AzureTest.startup()
            yield
        except Exception:
            logger.exception("startup error")
            raise
        finally:
            try:
                await AzureTest.shutdown()
            except Exception:
                logger.exception("shutdown error")
                raise

    application = AzureTestsService(
        title="AzureTest",
        version=__version__ or "1.0.0",
        lifespan=lifespan,
    )

    application.health_data.add_fastapi_readiness_route(application)
    application.health_data.add_fastapi_v1_health_route(application)

    enable_exception_handlers(application, obfuscate_validation_errors=False)

    return application


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80, factory=True)  # noqa: S104
