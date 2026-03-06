from starlette.testclient import TestClient
import json
from app.utils.password import get_authorization
from app.handlers.cognitive_search_handler import (cognitive_search_router, CatalogSearchRouter, AssetSearchRouter,
                                                   ResourceSearchRouter, ResourceAnalysisRouter, CatalogAnalysisRouter,
                                                   FormviewAnalysisRouter, FormviewSearchCatalogRouter,
                                                   FormviewAnalysisCatalogRouter)
from app.cores.cognitive_search.inputs import *

if __name__ == '__main__':
    # inputs = catalog_inputs_759298
    inputs = resource_inputs_no_auth


    Authorization = get_authorization("https://10.4.134.68", "common_user", "")
    print(Authorization)
    client = TestClient(cognitive_search_router)

    response = client.post(
        # CatalogAnalysisRouter,
        ResourceAnalysisRouter,
        headers={"Authorization": Authorization},
        json=inputs
    )
    response_dict = response.json()
    print(f"type of response = {type(response)}")
    print(f"type of response_dict = {type(response_dict)}")
    json_string = json.dumps(response_dict, indent=4, ensure_ascii=False)
    # with open("catalog_analysis_output_1.json", "w", encoding="utf-8") as json_file:
    with open("resource_analysis_output_1.json", "w", encoding="utf-8") as json_file:
        json_file.write(json_string)
    assert response.status_code == 200
    print(f"response.status_code = {response.status_code}")
