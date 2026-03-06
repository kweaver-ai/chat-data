from urllib.parse import urljoin

from app.cores.prompt.manage.api_base import API
from app.service.service_error import ConfigCenterError, BaseError
# from config import settings

class AfConfigService(object):
    configuration_center_url: str = "http://configuration-center:8133"

    def __init__(self):
        self._gen_api_url()

    def _gen_api_url(self):
        self.by_type_list_url = "/api/internal/configuration-center/v1/byType-list/{num}"

    async def get_config_dict(
        self,
        num: int | str
    ) -> list:
        url = urljoin(
            self.configuration_center_url,
            self.by_type_list_url
        ).format(num=num)
        api = API(
            url=url
        )
        try:
            res = await api.call_async()
            return res
        except BaseError as e:
            raise ConfigCenterError(e) from e
