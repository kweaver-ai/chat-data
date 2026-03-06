from config import settings
from opensearchpy import OpenSearch




class OpenSearchClient(object):

    def __init__(self):
        opensearch_read: str = settings.AF_OPENSEARCH_READ
        opensearch_port: str = settings.AF_OPENSEARCH_PORT
        opensearch_user: str = settings.AF_OPENSEARCH_USER
        opensearch_passwd: str = settings.AF_OPENSEARCH_PASS

        if settings.IF_DEBUG:
            opensearch_read_url = opensearch_read
        else:
            opensearch_read_url = "{}.resource".format(opensearch_read)
        auth = (opensearch_user, opensearch_passwd)
        self.client = OpenSearch(
            hosts=[{'host': opensearch_read_url, 'port': opensearch_port}],
            http_auth=auth,  # 如果需要认证
            use_ssl=False,  # 根据你的 OpenSearch 是否使用 SSL 进行调整
            verify_certs=False,  # 验证 SSL 证书
        )

    def search(self, input_index, input_query):
        response = self.client.search(
            index=input_index,
            body=input_query,
            scroll='5m'  # 滚动查询的过期时间（用于大数据集分页）
        )

        return response

