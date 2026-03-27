from app.service.af_config_service import AfConfigService
"""
    获取配置中心配置
"""


class GetServiceResult(AfConfigService):
    def __init__(self):
        super(GetServiceResult, self).__init__()

    async def paser_config_dict(
        self,
        num: int | str,
    ) -> dict:
        config = await self.get_config_dict(
            num
        )
        config_dict = {}
        for item in config:
            config_dict[item["key"]] = item["value"]
        return config_dict

    async def use_react_mode(
        self
    ) -> bool:
        config = await self.paser_config_dict(8)
        if config.get("sailor_agent_react_mode") == "true":
            return True
        return False

    async def direct_qa(
        self
    ) -> bool:
        config = await self.paser_config_dict(8)
        if config.get("direct_qa") == "true":
            return True
        return False

    async def get_max_input_token(
        self
    ) -> int:
        config = await self.paser_config_dict(9)
        if "sailor_agent_llm_input_len" in config:
            return int(config["sailor_agent_llm_input_len"])
        return 8000

    async def get_model_return_limit(
        self
    ) -> (int, int):
        config = await self.paser_config_dict(9)
        return_record_limit = -1
        if "sailor_agent_return_record_limit" in config:
            return_record_limit = int(config["sailor_agent_return_record_limit"])
        return_data_limit = -1
        if "sailor_agent_return_data_limit" in config:
            return_data_limit = int(config["sailor_agent_return_data_limit"])
        return return_record_limit, return_data_limit

    async def get_dimension_num_limit(
        self
    ) -> (int, int):
        config = await self.paser_config_dict(9)
        dimension_num_limit = -1
        if "dimension_num_limit" in config:
            dimension_num_limit = int(config["dimension_num_limit"])
        return dimension_num_limit

    async def get_data_market_llm_temperature(
        self
    ) -> (int, int):
        config = await self.paser_config_dict(9)
        data_market_llm_temperature = 0.2
        if "data_market_llm_temperature" in config:
            data_market_llm_temperature = float(config["data_market_llm_temperature"])
        return data_market_llm_temperature

    async def retriever_config(
        self
    ) -> int:
        config = await self.paser_config_dict(8)
        top_k = config.get("sailor_agent_indicator_recall_top_k")
        if top_k:
            return int(top_k)
        else:
            return 4

    async def search_dip_agent_key(
        self
    ) -> str:
        config = await self.paser_config_dict(8)
        agent_key = config.get("search_dip_agent_key")
        if agent_key:
            return agent_key
        else:
            return ""


if __name__ == "__main__":
    async def main():
        from app.utils.password import get_authorization
        Authorization = get_authorization("https://10.4.109.142", "liberly", "111111")
        service = GetServiceResult()
        res = await service.use_react_mode(

        )
        print(res)


    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
