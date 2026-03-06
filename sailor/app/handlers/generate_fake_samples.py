
from typing import List
from starlette.testclient import TestClient
from fastapi import APIRouter, Request

from app.cores.text2sql.sample_generate import SampleGenerate
from app.models.table_model import SampleGenerateInput, ColumnModel
from app.routers.generate_fake_samples import GenerateFakeSamples


generate_fake_samples_router = APIRouter()


@generate_fake_samples_router.post(GenerateFakeSamples, response_model=List[List[ColumnModel]])
async def text2sql_api(request: Request, params: SampleGenerateInput):
    a_sample_generator = SampleGenerate(
        header={"Authorization": request.headers.get('Authorization')})
    a_result = await a_sample_generator.generate_sample_v2(input_view_id=params.view_id, samples_size=params.samples_size,
                                                           user_id=params.user_id)
    return a_result


