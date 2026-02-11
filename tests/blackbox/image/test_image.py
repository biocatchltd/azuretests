from time import sleep
import requests




def test_readiness(azuretestsservice, base_url):
    resp = requests.get(base_url + "/api/readiness")
    assert resp.ok


def test_health(azuretestsservice, base_url):
    resp = requests.get(base_url + "/api/v1/health")
    assert resp.ok
    resp_data = resp.json()
    assert resp_data["version"]
    # sleep(10)
