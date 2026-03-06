import traceback
from app.logs.logger import logger
from urllib.parse import urljoin
from app.service.service_base import API
from app.service.service_error import DataCatalogError, BaseError


class AfDataView(object):
    data_view: str = "http://data-view:8123"

    debug: bool = False

    def __init__(self):
        self._gen_api_url()
        if self.debug:
            self.data_view = "http://10.4.109.142:8123"

    def _gen_api_url(self):
        self.model_info_url = "/api/data-view/v1/graph-model/{id}"
        self.sample_info_url = "/api/internal/data-view/v1/logic-view/{id}/synthetic-data"

    # 获取主题模型 专题模型详情
    async def get_model_info(
            self,
            model_id: str,
            token: str
    ) -> dict:
        url = urljoin(self.data_view, self.model_info_url).format(id=model_id)
        api = API(
            url=url.format(id=model_id),
            headers={"authorization": token}
        )
        try:
            response = await api.call_async()
            # mount_resource = response["mount_resource"][0]
            return {
                "id": response.get("id", ""),
                "business_name": response.get("business_name", ""),
                "meta_model_slice": response.get("meta_model_slice", []),
                "relations": response.get("relations", []),
                # "type": "4"
            }
        except BaseError as e:
            logger.error(e)
            raise DataCatalogError(e) from e
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())

    async def get_sample_data(self, view_id: str, token: str) -> dict:
        url = urljoin(self.data_view, self.sample_info_url).format(id=view_id)
        api = API(
            url=url,
            headers={"authorization": token}
        )
        try:
            response = await api.call_async()
            return response
        except BaseError as e:
            logger.error(e)
            raise DataCatalogError(e) from e
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
