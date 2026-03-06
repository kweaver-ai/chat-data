import re
from typing import Any, Union, List

from pydantic import BaseModel

from app.cores.cognitive_assistant.qa_api import FindNumberAPI
from app.logs.logger import logger
from app.utils.password import get_authorization


# 数据资源版 数据资源（包括逻辑视图、接口服务、指标）的数据结构
# class ViewAttribute(BaseModel):
class DataResourceAttribute(BaseModel):
    resourceid: Union[str, None] = None
    resourcename: Union[str, None] = None
    technical_name: Union[str, None] = None
    asset_type: Union[str, None] = None
    code: Union[str, None] = None
    description: Union[str, None] = None
    owner_id: Union[str, None] = None
    owner_name: Union[str, None] = None
    subject_id: Union[str, None] = None
    subject_name: Union[str, None] = None
    department_id: Union[str, None] = None
    department: Union[str, None] = None
    department_path_id: Union[str, None] = None
    department_path: Union[str, None] = None
    info_system_uuid: Union[str, None] = None
    info_system_name: Union[str, None] = None
    color: Union[str, None] = None
    published_at: Union[str, None] = None
    publish_status: Union[str, None] = None
    publish_status_category: Union[str, None] = None
    online_at: Union[str, None] = None
    online_status: Union[str, None] = None


class RetrieverAPI(FindNumberAPI):
    def __init__(self):
        super(RetrieverAPI, self).__init__()

    # async def get_column_info(self, idx: str, headers: dict) -> dict:
    #     col_info = await self.get_column_by_id(idx, headers)
    #     en2cn = {
    #         entries["technical_name"]: entries['business_name']
    #         for entries in col_info["columns"]
    #     }
    #     return en2cn

    async def get_data_catalog_column_info(self, idx: str, headers: dict) -> dict:
        '''
        根据数据目录的ID获取信息项，并筛选出所需数据

        Args:
            idx (str): 数据目录的ID
            headers (dict): HTTP请求头信息，包含认证信息等

        Returns:
            en2cn (dict): 字段技术名到业务名的映射字典
            格式: {"technical_name": "business_name"}

        Example:
            en2cn = await get_data_catalog_view_column_info("id-string", headers)
        '''
        col_info = await self.get_column_by_id(idx, headers)
        en2cn = {
            entries["technical_name"]: entries['business_name']
            for entries in col_info["columns"]
        }
        return en2cn

    async def get_svc_info(self, idx: str, headers: dict) -> tuple:
        svc_info = await self.get_params_by_id(idx, headers)
        req_en2cn = {
            entries["en_name"]: f'类型：{entries["data_type"]}， 解释：{entries["cn_name"]}， {entries["description"]}'
            for entries in svc_info["service_param"]["data_table_request_params"]
        }
        res_en2cn = {
            entries["en_name"]: entries["cn_name"]
            for entries in svc_info["service_param"]["data_table_response_params"]
        }
        status = svc_info["service_apply"]["audit_status"]
        status = "具有" if status == "pass" else "不具有"
        return req_en2cn, res_en2cn, status

    @staticmethod
    def extract_chinese(text):
        pattern = re.compile(r'[\u4e00-\u9fa5，。！？、；：“”‘’（）《》【】]+')
        matches = pattern.findall(text)
        return ''.join(matches)

    async def get_form_view_column_info(self, idx: str, headers: dict) -> tuple[dict[Any, Any], Any]:
        '''
        根据逻辑视图的UUID获取字段信息，并筛选出所需信息

        Args:
            idx (str): 逻辑视图的唯一标识符(UUID)
            headers (dict): HTTP请求头信息，包含认证信息等

        Returns:
            tuple[dict[Any, Any], Any]: 包含两个元素的元组
                - view_en2cn (dict): 字段技术名到业务名的映射字典
                  格式: {"technical_name": "business_name"}
                - view_source_catalog_name (Any): 逻辑视图的源

        Example:
            view_en2cn, source_name = await get_form_view_column_info("uuid-string", headers)
        '''
        view_column_info = await self.get_view_column_by_id(idx, headers)
        view_en2cn = {
            field["technical_name"]: field["business_name"]
            for field in view_column_info["fields"]
        }
        view_source_catalog_name = view_column_info["view_source_catalog_name"]

        return view_en2cn, view_source_catalog_name

    async def get_form_view_column_business_name(self, idx: str, headers: dict) -> List[str]:
        '''
        根据逻辑视图的UUID获取字段业务名称（中文名）

        Args:
            idx (str): 逻辑视图的唯一标识符(UUID)
            headers (dict): HTTP请求头信息，包含认证信息等

        Returns:
            List[str]: 包含逻辑视图所有字段业务名称的列表

        '''
        formview_column_info = await self.get_view_column_by_id(idx, headers)
        formview_column_business_name = [
            field["business_name"]
            for field in formview_column_info["fields"]
        ]

        return formview_column_business_name

    async def get_view_detail(self, idx: str, headers: dict) -> dict:
        view_detail = await self.get_view_detail_by_id(idx, headers)
        return view_detail

    async def get_indicator_analysis_dimensions_business_name(self, idx: str, headers: dict) -> List[str]:
        '''
        根据指标的雪花id（指标没有uuid）获取分析维度的业务名称（中文名）

        Args:
            idx (str): 指标的雪花id（指标没有uuid）
            headers (dict): HTTP请求头信息，包含认证信息等

        Returns:
            List[str]: 包含指标所有分析维度的业务名称的列表

        '''
        indicator_analysis_dimensions_info = await self.get_indicator_detail(idx, headers)
        indicator_analysis_dimensions_business_name = [
            dimension["business_name"]
            for dimension in indicator_analysis_dimensions_info["analysis_dimensions"]
        ]

        return indicator_analysis_dimensions_business_name

class Append(RetrieverAPI):
    def __init__(self):
        super().__init__()

    @staticmethod
    async def save_indicator_append(save_indicator, assets: DataResourceAttribute, headers):
        '''指标输出数据整理'''
        save_indicator.append(
            {
                "名称": assets.resourcename,
                "描述": assets.description
            }
        )
        return save_indicator

    async def save_catalog_append(self, save_catalog, save_catalog_cn, save_catalog_text2sql, assets, headers):
        '''数据目录输出数据整理'''

        logger.info(f'assets = {assets}')
        logger.info(f'开始整理数据目录, datacatalogid={assets["datacatalogid"]}')
        basic_info = await self.get_view_basic_info(assets["datacatalogid"], headers)
        print("===============")
        # print(basic_info)
        save_catalog.append(
            {
                "中文名": assets["datacatalogname"],
                "描述": assets["description_name"],
                "字段描述": await self.get_data_catalog_column_info(assets["datacatalogid"], headers)
            }
        )
        save_catalog_cn.append(
            {
                "中文名": assets["datacatalogname"],
                "描述": self.extract_chinese(assets["description_name"])
            }
        )
        save_catalog_text2sql.append(
            {
                'index': assets["datacatalogid"],
                'title': assets["datacatalogname"],
                'schema': assets["metadata_schema"],
                'source': assets["ves_catalog_name"],
                "description": assets["description_name"],
                "form_view_id": basic_info["form_view_id"],
                "technical_name": assets["technical_name"] if "technical_name" in assets else basic_info["technical_name"],
            }
        )
        return save_catalog, save_catalog_cn, save_catalog_text2sql

    async def save_svc_append(self, save_svc, save_svc_cn, save_svc_dict, assets, headers):
        '''接口服务输出数据整理'''
        require_en2cn, response_en2cn, audit_status = \
            await self.get_svc_info(assets["resourceid"], headers)
        save_svc.append(
            {
                "中文名": assets["resourcename"],
                "描述": assets["description"],
                "输入参数描述": require_en2cn,
            }
        )
        save_svc_cn.append(
            {
                "中文名": assets["resourcename"],
                "描述": self.extract_chinese(assets["description"])
            }
        )
        save_svc_dict[assets["resourcename"]] = \
            {
                "中文名": assets["resourcename"],
                "描述": assets["description"],
                "输入参数描述": require_en2cn,
                "返回参数描述": response_en2cn,
                "是否具有接口的调用权限": audit_status
            }
        return save_svc, save_svc_cn, save_svc_dict
    # save_props_dict 统一改名为 save_cites_dict， 因为数据结构和save_cites一样， 差别在于前者是dict，后者是list
    @staticmethod
    async def save_cites_append(save_cites, save_cites_dict: dict, assets):
        ''' 数据目录版 输出数据中 cites 部分整理 '''
        save_cites.append(
            {
                "id": assets["datacatalogid"],
                "code": assets["code"],
                "type": "interface_svc" if assets["asset_type"] == "2" else "data_catalog",
                "title": assets["datacatalogname"],
                "description": assets["description_name"],
                "connected_subgraph": assets["connected_subgraph"] if "connected_subgraph" in assets else None
            }
        )
        # print(f"save_cites = {save_cites}")
        save_cites_dict[assets["datacatalogname"]] = \
            {
                "id": assets["datacatalogid"],
                "code": assets["code"],
                "type": "interface_svc" if assets["asset_type"] == "2" else "data_catalog",
                "title": assets["datacatalogname"],
                "description": assets["description_name"],
            }
        # print(f"save_cites_dict = {save_cites_dict}")

        return save_cites, save_cites_dict

    # 数据资源版 输出数据中 cites 部分整理
    # @staticmethod
    async def save_resource_cites_append(self,save_cites: list, save_cites_dict: dict, assets,headers):
        ''' 数据资源版 输出数据中 cites 部分整理 '''
        data_map = {
            "1": "data_catalog",
            "2": "interface_svc",
            "3": "data_view",
            "4": "indicator",

        }
        # 获取逻辑视图的字段信息
        view_en2cn, view_source_catalog_name = await self.get_form_view_column_info(assets.resourceid, headers)
        # logger.info(f'in save_resource_cites_append, input assets = {assets} ')
        save_cites.append(
            {
                "id": assets.resourceid,
                "code": assets.code,
                "type": data_map[assets.asset_type],
                "title": assets.resourcename,
                "description": assets.description,
                "department": assets.department,
                "info_system": assets.info_system_name,
                "fields": view_en2cn,
            }
        )
        save_cites_dict[assets.resourcename] = \
            {
                "id": assets.resourceid,
                "code": assets.code,
                "type": data_map[assets.asset_type],
                "title": assets.resourcename,
                "description": assets.description,
                "department": assets.department,
                "info_system": assets.info_system_name,
                "fields": view_en2cn,
            }

        return save_cites, save_cites_dict

    async def save_view_append(self, save_view, save_view_cn, save_view_text2sql,
                               assets: DataResourceAttribute, headers):
        '''逻辑视图输出数据整理'''
        view_en2cn, view_source_catalog_name = await self.get_form_view_column_info(assets.resourceid, headers)
        save_view.append(
            {
                "resourceid": assets.resourceid,
                "中文名": assets.resourcename,
                "描述": assets.description,
                "字段描述": view_en2cn
            }
        )
        save_view_cn.append(
            {
                "resourceid": assets.resourceid,
                "中文名": assets.resourcename,
                "描述": self.extract_chinese(assets.description),
                "字段描述": view_en2cn
            }
        )
        detail = await self.get_view_detail(assets.resourceid, headers)
        # asset = {
        #     "index": assets.resourceid,
        #     "title": detail["technical_name"],
        #     "resource_name": detail["business_name"],
        #     "schema": "default",  # 逻辑全是默认： default
        #     "source": detail["view_source_catalog_name"][:-8],
        # }

        save_view_text2sql.append(
            {
                'index': assets.resourceid,
                'title': assets.technical_name,
                'schema': detail.get("schema", None),
                'source': detail.get("datasource_name", None),
                "description": assets.description,
                "resource_name": assets.resourcename,
                "view_source_catalog_name": view_source_catalog_name
            }
        )
        return save_view, save_view_cn, save_view_text2sql

async def main():
    ap =Append()
    auth = get_authorization("https://10.4.134.68", "", "")
    headers = {"Authorization": auth}
    formview_dict = {
                     }
    for key,value in formview_dict.items():
        print('-'*50)
        print(f'formview={key}')
        view_en2cn, view_source_catalog_name = await ap.get_form_view_column_info(value, headers=headers)
        print(f'view_en2cn={view_en2cn}')
        print(f'view_source_catalog_name={view_source_catalog_name}')


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())