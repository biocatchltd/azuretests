
import asyncio
import json

import uuid
from payload import build_payload_bytes
from env_vars import writes_per_second_ev, azure_share_name_ev
from azure.storage.fileshare.aio import ShareServiceClient
import datetime

reader_queue = asyncio.Queue()
deleter_queue = asyncio.Queue()

async def start_load(dir_client, metrics):
    writes_per_second = writes_per_second_ev.get()
    reades_per_second = int(writes_per_second * (1300 / 1500))
    deleters_per_second = int(writes_per_second * (1000 / 1500))
    print("writes_per_second", writes_per_second)

    tasks = [
        asyncio.create_task(writer_loop(writes_per_second, reades_per_second, deleters_per_second, dir_client, metrics)),
        asyncio.create_task(start_reader(reades_per_second, reades_per_second, deleters_per_second, dir_client, metrics)),
        asyncio.create_task(start_deleter(deleters_per_second, dir_client, metrics)),
    ]
    await asyncio.gather(*tasks)

async def writer_loop(writer_rate, read_rate, delete_rate, dir_client, metrics):
    print("writer loop started with rate", writer_rate)
    while True:
        try:
            t_start = asyncio.get_event_loop().time()
            awaited = []
            files = [str(uuid.uuid4()) for _ in range(writer_rate)]
            for file_name in files:
                # print("writing...", file_name)
                file_client = dir_client.get_file_client(file_name)
                awaited.append(file_client.upload_file(build_payload_bytes(file_name, 1)))
            await asyncio.gather(*awaited)
            for file_name in files[:read_rate]:
                await reader_queue.put(file_name)
            t_end = asyncio.get_event_loop().time()
            elapsed = t_end - t_start

            sleep_time = max(0, 1 - elapsed)
        except Exception as e:
            print(e)
            sleep_time = 1
            status = "error"
        else:
            status = "success"
        finally:
            metrics.timing("biocatch.azuretests.writer", value=elapsed, tags=[f"count:{writer_rate}"])
            metrics.increment("biocatch.azuretests.writer_counter", tags=[f"status:{status},count:{writer_rate}"])
        print(f"writer loop iteration took {elapsed:.2f}s, sleeping for {sleep_time:.2f}s")
        await asyncio.sleep(sleep_time)

async def start_reader(rate, reades_per_second, deleters_per_second, dir_client, metrics):
    print("reader loop started with rate", rate)
    while True:
        try:
            t_start = asyncio.get_event_loop().time()
            file_names = [await reader_queue.get() for _ in range(reades_per_second)]
            # Start all downloads in parallel
            download_tasks = [dir_client.get_file_client(file_name).download_file() for file_name in file_names]
            streams = await asyncio.gather(*download_tasks)
            # Read all contents in parallel
            read_tasks = [stream.readall() for stream in streams]
            contents = await asyncio.gather(*read_tasks)
            # Process all results
            for file_name, content in zip(file_names, contents):
                obj = json.loads(content.decode("utf-8"))
                # print("reading...", file_name, obj)
            for file_name in file_names[:deleters_per_second]:
                await deleter_queue.put(file_name)
            t_end = asyncio.get_event_loop().time()
            elapsed = t_end - t_start
            sleep_time = max(0, 1 - elapsed)
        except Exception as e:
            print(e)
            sleep_time = 1
            status = "error"
        else:
            status = "success"
        finally:
            metrics.timing("biocatch.azuretests.reader", value=elapsed, tags=[f"count:{reades_per_second}"])
            metrics.increment("biocatch.azuretests.reader_counter", tags=[f"status:{status},count:{reades_per_second}"])
        print(f"reader loop iteration took {elapsed:.2f}s, sleeping for {sleep_time:.2f}s")
        await asyncio.sleep(sleep_time)

async def start_deleter(rate, dir_client, metrics):
    print("deleter loop started with rate", rate)
    while True:
        try:
            t_start = asyncio.get_event_loop().time()
            file_names = [await deleter_queue.get() for _ in range(rate)]
            delete_tasks = []
            for file_name in file_names:
                file_client = dir_client.get_file_client(file_name)
                delete_tasks.append(file_client.delete_file())
                # print("deleting...", file_name)
            await asyncio.gather(*delete_tasks)
            t_end = asyncio.get_event_loop().time()
            elapsed = t_end - t_start
            sleep_time = max(0, 1 - elapsed)
        except Exception as e:
            print(e)
            sleep_time = 1
            status = "error"
        else:
            status = "success"
        finally:
            metrics.timing("biocatch.azuretests.deleter", value=elapsed, tags=[f"count:{rate}"])
            metrics.increment("biocatch.azuretests.deleter_counter", tags=[f"status:{status},count:{rate}"])
        print(f"deleter loop iteration took {elapsed:.2f}s, sleeping for {sleep_time:.2f}s")
        await asyncio.sleep(sleep_time)
        
if __name__ == "__main__":
    print("main")
    from env_vars import connection_string_ev

    async def main_async():
        connection_string = connection_string_ev.get()
        service_client = ShareServiceClient.from_connection_string(connection_string)
        share_name = azure_share_name_ev.get()
        directory_name = "load_tests"

        print("calling get_share_client")
        share_client = service_client.get_share_client(share_name)
        print("called get_share_client")

        dir_client = share_client.get_directory_client(directory_name)
        from unittest.mock import MagicMock
        await start_load(dir_client, MagicMock())

    asyncio.run(main_async())