from engine.api_client import ApiClient


def new_customer(base_url: str | None = None) -> ApiClient:
    boot = ApiClient(base_url=base_url)
    init = boot.customer.init()
    return ApiClient(token=init.access_token, base_url=base_url)
