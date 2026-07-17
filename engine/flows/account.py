from ..client import ApiClient


def new_account(base_url: str | None = None) -> ApiClient:
    boot = ApiClient(base_url=base_url)
    init = boot.account.init()
    return ApiClient(token=init.access_token, base_url=base_url)
