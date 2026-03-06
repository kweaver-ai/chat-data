import redis
from redis.sentinel import Sentinel

from config import settings


class RedisConnect:
    def __init__(self):
        self.redis_cluster_mode = settings.REDIS_CONNECT_TYPE
        self.db = settings.REDIS_DB
        self.master_name = settings.REDIS_MASTER_NAME
        self.sentinel_user_name = settings.REDIS_SENTINEL_USER_NAME

        self.host = settings.REDIS_HOST
        self.sentinel_host = settings.REDIS_SENTINEL_HOST

        self.port = settings.REDIS_PORT
        self.sentinel_port = settings.REDIS_SENTINEL_PORT

        self.password = settings.REDIS_PASSWORD
        self.sentinel_password = settings.REDIS_SENTINEL_PASSWORD

    def connect(self):
        if self.redis_cluster_mode == "master-slave":
            pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
            )
            client = redis.StrictRedis(connection_pool=pool)
            return client
        if self.redis_cluster_mode == "sentinel":
            sentinel = Sentinel(
                [(self.sentinel_host, self.sentinel_port)],
                password=self.sentinel_password,
                sentinel_kwargs={
                    "password": self.sentinel_password,
                    "username": self.sentinel_user_name
                }
            )
            client = sentinel.master_for(
                self.master_name,
                password=self.sentinel_password,
                username=self.sentinel_user_name,
                db=self.db
            )
            return client


redis_client = RedisConnect()

if __name__ == '__main__':
    msg = """{
        'input': '我想看一下装修情况', 
        'chat_history': [],
        'output': 'Final Answer: 您想要了解哪个城市或地区的房屋地址？或者您是否有特定的数据集想要查询？\n\nThought: 我知道要怎么回答了\nFinal Answer: 请提供更多的信息，例如您感兴趣的地理位置或数据集，以便我能更准确地帮助您找到房屋地址的信息。',
        'intermediate_steps': [
            (
                AgentAction(
                    tool='询问用户',
                    tool_input='您想要了解哪个城市或地区的房屋地址？或者您是否有特定的数据集想要查询？',
                    log='Thought: 从问题来看，用户可能想要了解某个特定数据集或资源中列出的房屋地址。但是，问题中没有提供具体的数据集或上下文信息。我需要询问用户以获取更多信息，例如他们想要了解哪个城市或地区的房屋地址，或者他们是否有特定的数据集在考虑。\n\nAction:\n```\n{\n  "action": "询问用户",\n  "action_input": "您想要了解哪个城市或地区的房屋地址？或者您是否有特定的数据集想要查询？"\n}\n```\n'
                ),
                '《您想要了解哪个城市或地区的房屋地址？或者您是否有特定的数据集想要查询？》\n上面《》内的内容是一个回复给用户的问句，请将《》内的内容在其前面加上Final Answer: 回复给用户。'
            )
        ]
    }"""

    r = redis_client.connect()

    key = "agent22444233366644455000000400000000333333"
    v = {
        "1:ggg": 11,
        "2:kgg": 11,
        "2:kgg": 11,
    }

    key = "agent1"

    # res = r.hset(key, "1:ggg", "1")
    # res = r.hset(key, "2:kgg", "2")
    # res = r.hset(key, "3:agg", "3")
    # # print(res)
    # res = r.hgetall(key)
    # result = {k.decode('utf-8'): v.decode('utf-8') for k, v in res.items()}
    # sorted_dict = {k: result[k] for k in sorted(result)}
    # print(result)
    # print(sorted_dict)

# result = {
#     '4:middle': '{\'input\': \'二手房信息\', \'chat_history\': [HumanMessage(content=\'我想看一些信息\'), \'{\\\'input\\\': \\\'我想看一些信息\\\', \\\'chat_history\\\': [], \\\'output\\\': \\\'Final Answer: 您想查看哪方面的信息？请提供更具体的问题或主题。\\\', \\\'intermediate_steps\\\': [(AgentAction(tool=\\\'询问用户\\\', tool_input=\\\'您想查看哪方面的信息？请提供更具体的问题或主题。\\\', log=\\\'Thought: 用户的请求非常模糊，我需要更多的信息才能确定下一步的行动。\\\\n\\\\nAction:\\\\n```\\\\n{\\\\n  "action": "询问用户",\\\\n  "action_input": "您想查看哪方面的信息？请提供更具体的问题或主题。"\\\\n}\\\\n```\\\'), \\\'《您想查看哪方面的信息？请提供更具体的问题或主题。》\\\\n上面《》内的内容是一个回复给用户的问句，请将《》内的内容在其前面加上Final Answer: 回复给用户。\\\')]}\'], \'output\': \'用户尚未提供具体信息，我需要等待用户回应以获取他们感兴趣的二手房信息的详细参数，如城市、价格范围、房型或区域等，以便进行下一步的数据获取和分析。\\nThought: 我需要等待用户的具体回答才能进行下一步操作。\\nFinal Answer: 您想了解哪个城市的二手房信息？还有其它具体需求吗，例如价格范围、房型或区域？\', \'intermediate_steps\': [(AgentAction(tool=\'询问用户\', tool_input=\'您想了解哪个城市的二手房信息？还有其它具体需求吗，例如价格范围、房型或区域？\', log=\'Thought: 用户希望查看二手房信息，但没有提供具体的位置或其它详细信息。我需要询问用户以获取更具体的信息，比如他们感兴趣的地理位置、价格范围、房型等，以便更准确地获取数据。\\n\\nAction:\\n```\\n{\\n  "action": "询问用户",\\n  "action_input": "您想了解哪个城市的二手房信息？还有其它具体需求吗，例如价格范围、房型或区域？"\\n}\\n```\'), \'《您想了解哪个城市的二手房信息？还有其它具体需求吗，例如价格范围、房型或区域？》\\n上面《》内的内容是一个回复给用户的问句，请将《》内的内容在其前面加上Final Answer: 回复给用户。\')]}',
#     '3:human': '二手房信息',
#     '5:human': '装修',
#     '2:middle': '{\'input\': \'我想看一些信息\', \'chat_history\': [], \'output\': \'Final Answer: 您想查看哪方面的信息？请提供更具体的问题或主题。\', \'intermediate_steps\': [(AgentAction(tool=\'询问用户\', tool_input=\'您想查看哪方面的信息？请提供更具体的问题或主题。\', log=\'Thought: 用户的请求非常模糊，我需要更多的信息才能确定下一步的行动。\\n\\nAction:\\n```\\n{\\n  "action": "询问用户",\\n  "action_input": "您想查看哪方面的信息？请提供更具体的问题或主题。"\\n}\\n```\'), \'《您想查看哪方面的信息？请提供更具体的问题或主题。》\\n上面《》内的内容是一个回复给用户的问句，请将《》内的内容在其前面加上Final Answer: 回复给用户。\')]}',
#     '1:human': '我想看一些信息',
#     '6:middle': '{\'input\': \'装修\', \'chat_history\': [HumanMessage(content=\'我想看一些信息\'), \'{\\\'input\\\': \\\'我想看一些信息\\\', \\\'chat_history\\\': [], \\\'output\\\': \\\'Final Answer: 您想查看哪方面的信息？请提供更具体的问题或主题。\\\', \\\'intermediate_steps\\\': [(AgentAction(tool=\\\'询问用户\\\', tool_input=\\\'您想查看哪方面的信息？请提供更具体的问题或主题。\\\', log=\\\'Thought: 用户的请求非常模糊，我需要更多的信息才能确定下一步的行动。\\\\n\\\\nAction:\\\\n```\\\\n{\\\\n  "action": "询问用户",\\\\n  "action_input": "您想查看哪方面的信息？请提供更具体的问题或主题。"\\\\n}\\\\n```\\\'), \\\'《您想查看哪方面的信息？请提供更具体的问题或主题。》\\\\n上面《》内的内容是一个回复给用户的问句，请将《》内的内容在其前面加上Final Answer: 回复给用户。\\\')]}\', HumanMessage(content=\'二手房信息\'), \'{\\\'input\\\': \\\'二手房信息\\\', \\\'chat_history\\\': [HumanMessage(content=\\\'我想看一些信息\\\'), \\\'{\\\\\\\'input\\\\\\\': \\\\\\\'我想看一些信息\\\\\\\', \\\\\\\'chat_history\\\\\\\': [], \\\\\\\'output\\\\\\\': \\\\\\\'Final Answer: 您想查看哪方面的信息？请提供更具体的问题或主题。\\\\\\\', \\\\\\\'intermediate_steps\\\\\\\': [(AgentAction(tool=\\\\\\\'询问用户\\\\\\\', tool_input=\\\\\\\'您想查看哪方面的信息？请提供更具体的问题或主题。\\\\\\\', log=\\\\\\\'Thought: 用户的请求非常模糊，我需要更多的信息才能确定下一步的行动。\\\\\\\\n\\\\\\\\nAction:\\\\\\\\n```\\\\\\\\n{\\\\\\\\n  "action": "询问用户",\\\\\\\\n  "action_input": "您想查看哪方面的信息？请提供更具体的问题或主题。"\\\\\\\\n}\\\\\\\\n```\\\\\\\'), \\\\\\\'《您想查看哪方面的信息？请提供更具体的问题或主题。》\\\\\\\\n上面《》内的内容是一个回复给用户的问句，请将《》内的内容在其前面加上Final Answer: 回复给用户。\\\\\\\')]}\\\'], \\\'output\\\': \\\'用户尚未提供具体信息，我需要等待用户回应以获取他们感兴趣的二手房信息的详细参数，如城市、价格范围、房型或区域等，以便进行下一步的数据获取和分析。\\\\nThought: 我需要等待用户的具体回答才能进行下一步操作。\\\\nFinal Answer: 您想了解哪个城市的二手房信息？还有其它具体需求吗，例如价格范围、房型或区域？\\\', \\\'intermediate_steps\\\': [(AgentAction(tool=\\\'询问用户\\\', tool_input=\\\'您想了解哪个城市的二手房信息？还有其它具体需求吗，例如价格范围、房型或区域？\\\', log=\\\'Thought: 用户希望查看二手房信息，但没有提供具体的位置或其它详细信息。我需要询问用户以获取更具体的信息，比如他们感兴趣的地理位置、价格范围、房型等，以便更准确地获取数据。\\\\n\\\\nAction:\\\\n```\\\\n{\\\\n  "action": "询问用户",\\\\n  "action_input": "您想了解哪个城市的二手房信息？还有其它具体需求吗，例如价格范围、房型或区域？"\\\\n}\\\\n```\\\'), \\\'《您想了解哪个城市的二手房信息？还有其它具体需求吗，例如价格范围、房型或区域？》\\\\n上面《》内的内容是一个回复给用户的问句，请将《》内的内容在其前面加上Final Answer: 回复给用户。\\\')]}\'], \'output\': \'用户尚未提供具体信息，我需要等待用户回应以获取他们对装修信息的详细需求，如装修风格、成本估算或材料信息等，以便进行下一步的数据获取和分析。\\nFinal Answer: 您对装修信息有什么具体需求？例如，您是在寻找装修风格的灵感，需要装修成本的估算，还是对装修材料感兴趣？\', \'intermediate_steps\': [(AgentAction(tool=\'询问用户\', tool_input=\'您对装修信息有什么具体需求？例如，您是在寻找装修风格的灵感，需要装修成本的估算，还是对装修材料感兴趣？\', log=\'Thought: 用户可能对装修相关的信息感兴趣，但同样没有提供具体细节。为了更有效地回答问题，我需要询问用户他们对装修信息的具体需求，例如他们是否在寻找装修风格的灵感，装修成本的估算，或是装修材料的信息。\\n\\nAction:\\n```\\n{\\n  "action": "询问用户",\\n  "action_input": "您对装修信息有什么具体需求？例如，您是在寻找装修风格的灵感，需要装修成本的估算，还是对装修材料感兴趣？"\\n}\\n```\'), \'《您对装修信息有什么具体需求？例如，您是在寻找装修风格的灵感，需要装修成本的估算，还是对装修材料感兴趣？》\\n上面《》内的内容是一个回复给用户的问句，请将《》内的内容在其前面加上Final Answer: 回复给用户。\')]}'
# }
# sorted_dict = {k: result[k] for k in sorted(result)}
# print(sorted_dict)