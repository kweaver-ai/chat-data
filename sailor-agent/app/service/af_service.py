from app.logs.logger import logger
from app.service.service_error import DataCatalogError, BaseError
from app.service.service_base import API
from app.utils.password import get_authorization
from app.cores.data_mart_qa.models import DataMartQAModel
from urllib.parse import urljoin
import traceback
import sys
sys.path.append("/mnt/pan/zkn/code_sdk/af_sailor_agent_687639/af-sailor-agent")


class AfService(object):
    data_catalog: str = "http://data-catalog:8153"

    debug: bool = False

    def __init__(self):
        self._gen_api_url()
        if self.debug:
            self.data_catalog = "http://10.4.109.142:8153"

    def _gen_api_url(self):
        self.mount = "/api/data-catalog/frontend/v1/data-catalog/{catalog_id}/mount"
        self.search_1 = "/api/data-catalog/frontend/v1/data-resources/search"
        self.search_2 = "/api/data-catalog/frontend/v1/data-resources/searchForOper"
        self.search_3 = "/api/data-catalog/frontend/v1/data-catalog/search"
        self.search_4 = "/api/data-catalog/frontend/v1/data-catalog/operation/search"

    async def get_mount(
        self,
        catalog_id: str,
        token: str
    ) -> dict:
        url = urljoin(self.data_catalog, self.mount).format(
            catalog_id=catalog_id)
        api = API(
            url=url.format(catalog_id=catalog_id),
            headers={"authorization": token}
        )
        try:
            response = await api.call_async()
            mount_resource = response["mount_resource"][0]
            return {
                "id": mount_resource.get("resource_id"),
                "type": "3"
            }
        except BaseError as e:
            logger.error(e)
            raise DataCatalogError(e) from e
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())

    async def func_verify_online(
        self,
        headers: dict,
        ids: list,
        search_id_url: str
    ):
        resource_id_name = []
        url = urljoin(self.data_catalog, search_id_url)
        api = API(
            url=url,
            headers=headers,
            method="POST",
            payload={"filter": {"ids": ids}}
        )
        try:
            res = await api.call_async()
            if res["total_count"] > 0:
                for entry in res["entries"]:
                    if entry["is_publish"] and entry["is_online"]:                    
                        resource_id_name.append(entry['id'])                      
                            
            return resource_id_name
        except BaseError as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            raise DataCatalogError(e) from e
       

    async def check_resource_status(
        self,
        params: DataMartQAModel
    ):
        try:
            # 查验资源是否可用是否为线上
            # 1是资源版非数据运营开发，2是资源版数据运营开发  ，3是目录版非数据运营开发，  4是目录版数据运行开发
            headers = {"authorization": params.token}
            ids = [source.id for source in params.resources]
            roles = params.roles
            if "data-operation-engineer" in roles or "data-development-engineer" in roles:
                if params.af_editions == "catalog":
                    res = await self.func_verify_online(headers, ids, self.search_4)
                else:
                    res = await self.func_verify_online(headers, ids, self.search_2)
            else:
                if params.af_editions == "catalog":
                    res = await self.func_verify_online(headers, ids, self.search_3)
                else:
                    res = await self.func_verify_online(headers, ids, self.search_1)
            return res
        
        except DataCatalogError as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            raise DataCatalogError(e) from e
        


if __name__ == "__main__":
    service = AfService()
    
    
    
    import asyncio
    res = asyncio.run(
        service.get_mount(
            catalog_id="540164499651439238",
            token=get_authorization(
                "https://10.4.109.216", "liberly", "111111")
        )
    )
    print(res)
