def get_url(name, source="", idx=""):
    ip = "https://10.4.109.234"
    if name == "configuration_center":
        return f"{ip}/api/configuration-center/v1/datasource?keyword={source}"
    elif name == "virtual_engine_service":
        return f"{ip}/api/virtual_engine_service/v1/fetch"
    elif name == "data_catalog":
        return f"{ip}/api/data-catalog/frontend/v1/data-catalog/search/cog"
    elif name == "data_catalog_common":
        return f"{ip}/api/data-catalog/frontend/v1/data-catalog/{idx}/common"
    elif name == "data_catalog_column":
        return f"{ip}/api/data-catalog/frontend/v1/data-catalog/{idx}/column"
