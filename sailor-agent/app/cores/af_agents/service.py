from app.service import ADPService
from app.cores.af_agents.models import AgentQAModel

class AgentService(object):

    def __init__(self):
        self.adp_service = ADPService()


    async def stream(self, params: AgentQAModel, authorization: str):
        adp_params = {
            "agent_id": params.agent_id,
            "agent_key": params.agent_key,
            "agent_version": params.agent_version,
            "query": params.query,
            "stream": params.stream,
            "inc_stream": params.inc_stream,
            "conversation_id": params.conversation_id

        }
        async for data in self.adp_service.stream_chat_v2(adp_params, authorization):

            yield data