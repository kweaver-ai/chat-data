import os
import asyncio
import ahocorasick, ast, jieba, json, math, numpy, re, time
from typing import Dict, Optional, List, Any
import numpy as np
from pydantic import BaseModel
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from starlette import status
from app.cores.cognitive_assistant.qa_api import FindNumberAPI
# from app.cores.cognitive_search.sdk_utils import (ad_builder_download_lexicon, ad_opensearch_connector, m3e_embeddings,
#                                                   ad_opensearch_connector_dip, custom_search_graph_call_dip)
from app.cores.cognitive_search.search_model import ANALYSIS_SEARCH_EMPTY_RESULT
from app.cores.cognitive_search.search_config.get_params import get_search_configs
from app.cores.cognitive_search.utils.utils import safe_str_to_int, safe_str_to_float
from app.cores.prompt.manage.ad_service import PromptServices
from app.cores.prompt.manage.payload_prompt import prompt_map
from app.logs.logger import logger
from app.utils.exception import NewErrorBase, ErrVal
from app.utils.stop_word import get_default_stop_words
from config import settings

prompt_svc = PromptServices()
find_number_api = FindNumberAPI()
base_path = os.path.dirname(os.path.abspath(__file__))
synonym_file_path = os.path.join(base_path, "resources/synonym_lexicon")
stopwords_file_path = os.path.join(base_path, "resources/stopwords_lexicon")


# 词频向量化
def get_word_vector(list_a, list_b, all_words):
    la = []
    lb = []
    for word in all_words:
        la.append(list_a.count(word))
        lb.append(list_b.count(word))
    return la, lb

# 计算余弦值
def calculate_cos(list_a, list_b):
    all_words = list(set(list_a + list_b))
    la, lb = get_word_vector(list_a, list_b, all_words)
    laa = numpy.array(la)
    lbb = numpy.array(lb)
    cos = (numpy.dot(laa, lbb.T)) / (((math.sqrt(numpy.dot(laa, laa.T))) * (math.sqrt(numpy.dot(lbb, lbb.T)))) + 0.01)
    return cos


def calculate_cosine_similarity(text1, text2):
    vectorizer = CountVectorizer()
    corpus = [text1, text2]
    vectors = vectorizer.fit_transform(corpus)
    similarity = cosine_similarity(vectors)
    return similarity[0][1]

def lev_dis_score(a, b):
    # its是匹配上的词（已去重）
    its = set(a).intersection(set(b))
    # 计算匹配上的词占总query分词数的百分比，乘以10 之后大致是0-10以内的数
    score_class = round(len(its) / (len(a) + 0.01), 2)
    # 统计分词query在属性值中一共出现多少次
    score_num = 0
    for i in a:
        c = b.count(i)
        score_num += c
    # 计算匹配上的词占字符总数的百分比
    score = round(len(its) / (len(b) + 0.01), 2) if len(b) != 0 else 0
    return score_class, score_num, score


# explore_result字段特殊处理，解析json后取key和result
def cut_explore_result(s):
    """explore_result 字段特殊处理，解析json后取 key 和 result """
    s = str(s).lower()

    try:
        dicts = ast.literal_eval(s)
    except:
        logger.error(f"json parse error: {s}")
        return [s]
    if not dicts:
        return []
    keywords = []
    if not isinstance(dicts, list):
        return [str(dicts)]
    for dic in dicts:
        if not isinstance(dic, dict):
            keywords.append(str(dic))
        for key in dic.keys():
            if key in ['key', 'result']:
                keywords.append(str(dic[key]))

    keywords = list(filter(None, keywords))
    return keywords


# 按中英文分割，标点符号分割
def cut_by_punc(s):
    # """按中英文分割，标点符号分割
    # >>> s = "/ref/header/main陈玉龙 和 Joyce，速度66快，xxx6 6-xxx"
    # >>> cut_by_punc(s)
    # ['/', 'ref', '/', 'header', '/', 'main', '陈玉龙', ' ', '和', ' ', 'Joyce', '，', '速度', '66', '快', '，', 'xxx6', ' ', '6', '-', 'xxx']
    #
    # :param s: String
    # :return:
    # """
    rgr = re.findall(r'(\w*)(\W*)', s)
    cuts = []
    for tup in rgr:
        if tup[0]:
            beg = 0
            flag = -1  # 0: en, 1: zh
            for i, ch in enumerate(tup[0]):
                if 'a' <= ch <= 'z' or '0' <= ch <= '9' or 'A' <= ch <= 'Z':
                    cur_flag = 0
                else:
                    cur_flag = 1
                if flag == -1 or cur_flag == flag:
                    flag = cur_flag
                    continue
                else:
                    cuts.append(tup[0][beg:i])
                    beg = i
                    flag = cur_flag
            if beg < len(tup[0]):
                cuts.append(tup[0][beg:])

        if tup[1]:
            cuts.append(tup[1])
    return cuts


# props_lst是一个由dict组成的list，查找某个key：value的列表index
def find_idx_list_of_dict_old(props_lst, key_to_find, value_to_find):
    try:
        for i in range(len(props_lst)):
            if props_lst[i][key_to_find] == value_to_find:
                idx = i
                return idx
    except:
        logger.error(f"datacatalog entity hasn't property {key_to_find}：{value_to_find} error: {props_lst}")
        raise Exception(f"datacatalog entity hasn't property {key_to_find}：{value_to_find} error: {props_lst}")


def find_idx_list_of_dict(props_lst, key_to_find, value_to_find):
    try:
        for i in range(len(props_lst)):
            if props_lst[i][key_to_find] == value_to_find:
                idx = props_lst[i]["value"]
                return idx
    except:
        logger.error(f"datacatalog entity hasn't property {key_to_find}：{value_to_find} error: {props_lst}")
        raise Exception(f"datacatalog entity hasn't property {key_to_find}：{value_to_find} error: {props_lst}")


def find_value_list_of_dict(props_lst, value_to_find):
    try:
        for i in range(len(props_lst)):
            if props_lst[i]['target'] == value_to_find:
                return props_lst[i]['source']
    except:
        logger.error(f"datacatalog entity hasn't property {value_to_find} error: {props_lst}")


# 同义词
def set_actrie_dip()->Optional[ahocorasick.Automaton]:
    """
        从本地文件读取同义词库构建Aho-Corasick Trie树

        Args:
            synonym_file_path: 同义词文件路径
            sep: 同义词之间的分隔符

        Returns:
            构建好的Aho-Corasick Automaton对象或None
        """

    sep = ';'
    try:
        # 从本地文件读取同义词内容
        with open(synonym_file_path, 'r', encoding='utf-8') as f:
            synonym_content = f.read()

        # 移除BOM字符（如果存在）
        if isinstance(synonym_content, str):
            synonym_content = synonym_content.lstrip('\ufeff')

        logger.info(f"从本地文件读取同义词库: {synonym_file_path}")

        if not synonym_content:
            logger.warning('同义词库文件为空')
            return None

        # synonym_content = ad_builder_download_lexicon(ad_appid, synonym_id)
        # # 如果是 bytes，使用 UTF-8 解码并移除 BOM
        # if isinstance(synonym_content, bytes):
        #     logger.info(f"isinstance(synonym_content, bytes)")
        #     synonym_content = synonym_content.decode('utf-8-sig')
        # elif isinstance(synonym_content, str):
        #     logger.info(f"isinstance(synonym_content, str)")
        #     synonym_content = synonym_content.lstrip('\ufeff')
        # logger.info(f"synonym_content={synonym_content}")

        if not isinstance(synonym_content, str):

            logger.error('Download synonym dict failed.')
            msg = synonym_content
            if 'LexiconIdNotExist' in msg['ErrorCode']:
                raise NewErrorBase(statu_code=status.HTTP_400_BAD_REQUEST,
                                   err_code=ErrVal.Err_Synonym_LexiconID_Err,
                                   cause=msg['ErrorDetails'] + 'Please check the synonym_id in config file.'
                                   )
            elif 'ParamError' in msg['ErrorCode']:
                raise NewErrorBase(statu_code=status.HTTP_400_BAD_REQUEST,
                                   err_code=ErrVal.Err_Args_Err,
                                   cause=msg['ErrorDetails'])
            else:
                raise NewErrorBase(statu_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                   err_code=ErrVal.Err_Internal_Err,
                                   cause=msg['ErrorDetails'])
        lines = synonym_content.split('\n')
        lines.pop(0)
        if len(lines) == 0:
            return None
        actrie = ahocorasick.Automaton()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            elems = line.split(sep)
            for i, elem in enumerate(elems):
                # logger.debug(f'i={i} elem={elem}')
                word = elem.lower().replace(' ', '')
                # logger.debug(f'word={word}')
                syns = [elems[i]] + elems[:i] + elems[i + 1:]
                # logger.debug(f'syns={syns}')
                # actrie.add_word(key=word, value=tuple(syns))  不接受keywod参数， 会报错
                actrie.add_word(word, tuple(syns))
        actrie.make_automaton()
        return actrie
    except Exception as e:
        logger.error(str(e))
        return None

# 同义词
def set_actrie(ad_appid:str, synonym_id:str, sep:str)->Optional[ahocorasick.Automaton]:
    try:
        synonym_content = ad_builder_download_lexicon(ad_appid, synonym_id)
        # # 如果是 bytes，使用 UTF-8 解码并移除 BOM
        # if isinstance(synonym_content, bytes):
        #     logger.info(f"isinstance(synonym_content, bytes)")
        #     synonym_content = synonym_content.decode('utf-8-sig')
        # elif isinstance(synonym_content, str):
        #     logger.info(f"isinstance(synonym_content, str)")
        #     synonym_content = synonym_content.lstrip('\ufeff')
        # logger.info(f"synonym_content={synonym_content}")

        if not isinstance(synonym_content, str):

            logger.error('Download synonym dict failed.')
            msg = synonym_content
            if 'LexiconIdNotExist' in msg['ErrorCode']:
                raise NewErrorBase(statu_code=status.HTTP_400_BAD_REQUEST,
                                   err_code=ErrVal.Err_Synonym_LexiconID_Err,
                                   cause=msg['ErrorDetails'] + 'Please check the synonym_id in config file.'
                                   )
            elif 'ParamError' in msg['ErrorCode']:
                raise NewErrorBase(statu_code=status.HTTP_400_BAD_REQUEST,
                                   err_code=ErrVal.Err_Args_Err,
                                   cause=msg['ErrorDetails'])
            else:
                raise NewErrorBase(statu_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                   err_code=ErrVal.Err_Internal_Err,
                                   cause=msg['ErrorDetails'])
        lines = synonym_content.split('\n')
        lines.pop(0)
        if len(lines) == 0:
            return None
        actrie = ahocorasick.Automaton()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            elems = line.split(sep)
            for i, elem in enumerate(elems):
                # logger.debug(f'i={i} elem={elem}')
                word = elem.lower().replace(' ', '')
                # logger.debug(f'word={word}')
                syns = [elems[i]] + elems[:i] + elems[i + 1:]
                # logger.debug(f'syns={syns}')
                # actrie.add_word(key=word, value=tuple(syns))  不接受keywod参数， 会报错
                actrie.add_word(word, tuple(syns))
        actrie.make_automaton()
        return actrie
    except Exception as e:
        logger.error(str(e))
        return None

# 停用词
def set_stopwords_dip()->Optional[List]:

    try:
        # 从本地文件读取同义词内容
        with open(stopwords_file_path, 'r', encoding='utf-8') as f:
            stopwords_content = f.read()

        # 移除BOM字符（如果存在）
        if isinstance(stopwords_content, str):
            stopwords_content = stopwords_content.lstrip('\ufeff')

        logger.info(f"从本地文件读取停用词库: {stopwords_file_path}")

        if not stopwords_content:
            logger.warning('停用词库文件为空')
            return None
        # stopwords_content = ad_builder_download_lexicon(ad_appid, stopwords_lid)
        if not isinstance(stopwords_content, str):
            logger.error('Download stopwords dict failed.')
            msg = stopwords_content
            if 'LexiconIdNotExist' in msg['ErrorCode']:
                raise NewErrorBase(statu_code=status.HTTP_400_BAD_REQUEST,
                                   err_code=ErrVal.Err_Synonym_LexiconID_Err,
                                   cause=msg['ErrorDetails'] + 'Please check the synonym_id in config file.')
            elif 'ParamError' in msg['ErrorCode']:
                raise NewErrorBase(statu_code=status.HTTP_400_BAD_REQUEST,
                                   err_code=ErrVal.Err_Args_Err,
                                   cause=msg['ErrorDetails'])
            else:
                raise NewErrorBase(statu_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                   err_code=ErrVal.Err_Internal_Err,
                                   cause=msg['ErrorDetails'])
        lines = stopwords_content.split('\n')
        lines.pop(0)
        stopwords = [line.strip() for line in lines]
        # logger.info(f'stopwords = {stopwords}')
        return stopwords
    except Exception as e:
        logger.error(str(e))
        return []


# 停用词
def set_stopwords(ad_appid:str, stopwords_lid:str)->Optional[List]:
    if stopwords_lid is None:
        return []
    try:
        stopwords_content = ad_builder_download_lexicon(ad_appid, stopwords_lid)
        if not isinstance(stopwords_content, str):
            logger.error('Download stopwords dict failed.')
            msg = stopwords_content
            if 'LexiconIdNotExist' in msg['ErrorCode']:
                raise NewErrorBase(statu_code=status.HTTP_400_BAD_REQUEST,
                                   err_code=ErrVal.Err_Synonym_LexiconID_Err,
                                   cause=msg['ErrorDetails'] + 'Please check the synonym_id in config file.')
            elif 'ParamError' in msg['ErrorCode']:
                raise NewErrorBase(statu_code=status.HTTP_400_BAD_REQUEST,
                                   err_code=ErrVal.Err_Args_Err,
                                   cause=msg['ErrorDetails'])
            else:
                raise NewErrorBase(statu_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                   err_code=ErrVal.Err_Internal_Err,
                                   cause=msg['ErrorDetails'])
        lines = stopwords_content.split('\n')
        lines.pop(0)
        stopwords = [line.strip() for line in lines]
        return stopwords
    except Exception as e:
        logger.error(str(e))
        return []




def init_lexicon_dip() -> Dict:
    """
    """
    resource = {}
    # 获取停用词词库 stopwords
    syn_actrie = set_actrie_dip()
    # 获取停用词词库 stopwords
    stopwords = set_stopwords_dip()
    resource['lexicon_actrie'] = syn_actrie
    resource['stopwords'] = stopwords
    return resource

def init_lexicon(ad_appid:str, required_resource: Dict) -> Dict:
# def init_func(ad_appid:str, required_resource: Dict) -> Dict:
    """
    Initialize resources for processing based on the provided application ID and required resource configuration.

    This function retrieves and processes two types of lexicons: a synonym lexicon and a stopwords lexicon.
    It constructs an Aho-Corasick trie (actrie) for the synonym lexicon if available, and loads the stopwords
    lexicon into a set. The resulting resources are returned as a dictionary.

    Parameters
    ----------
    ad_appid : str
        The application ID used to identify the context for resource initialization.
    required_resource : Dict
        A dictionary containing configuration details for the required resources. It may include keys
        such as 'lexicon_actrie' and 'stopwords', each representing a specific lexicon configuration.

    Returns
    -------
    Dict
        A dictionary containing the initialized resources. The keys include:
        - 'lexicon_actrie': The constructed Aho-Corasick trie for synonyms, or None if not applicable.
        - 'stopwords': A set of stopwords loaded from the stopwords lexicon, or an empty set if not applicable.

    Args Details
    ------------
    ad_appid:
        Identifies the application context. Used to fetch lexicon-specific resources.
    required_resource:
        Contains nested dictionaries for lexicon configurations. Each lexicon configuration may include:
        - 'lexicon_id': Identifier for the lexicon in the resource system.
        - 'lexicon_sep': Separator used in the lexicon data (default is ';').

    Returns Details
    ---------------
    The returned dictionary includes:
    - 'lexicon_actrie': Represents the Aho-Corasick trie built from the synonym lexicon. If no lexicon ID
      is provided, this will be None.
    - 'stopwords': A set of stopwords extracted from the stopwords lexicon. If no lexicon ID is provided,
      this will be an empty set.

    Notes
    -----
    The function assumes that helper functions `set_actrie` and `set_stopwords` are defined elsewhere
    and handle the actual construction and loading of the respective resources.
    """
    resource = {}
    # "required_resource": {
    #     "lexicon_actrie": {
    #       "lexicon_id": "46"
    #     },
    #     "stopwords": {
    #       "lexicon_id": "47"
    #     }
    #   }
    # 获取同义词词库 lexicon_actrie
    syn_lexicon = required_resource.get('lexicon_actrie', {})
    # logger.debug(f'syn_lexicon =  {syn_lexicon}')
    # syn_lexicon_id = None if not syn_lexicon else syn_lexicon.get('lexicon_id', None)
    syn_lexicon_id = syn_lexicon.get('lexicon_id', None)
    # logger.debug(f'syn_lexicon_id =  {syn_lexicon_id}')
    # syn_lexicon_sep = ';' if not syn_lexicon else syn_lexicon.get('lexicon_sep', ';')
    syn_lexicon_sep = syn_lexicon.get('lexicon_sep', ';')
    # 构建actrie
    if syn_lexicon_id is None:
        syn_actrie = None
    else:
        syn_actrie = set_actrie(ad_appid, syn_lexicon_id, syn_lexicon_sep)
    # 获取停用词词库 stopwords
    stopwords_lexicon = required_resource.get('stopwords', {})
    # stopwords_lexicon_id = None if not stopwords_lexicon else stopwords_lexicon.get('lexicon_id', None)
    stopwords_lexicon_id = stopwords_lexicon.get('lexicon_id', None)
    # 加载停用词词库
    if stopwords_lexicon_id is None:
        stopwords = []
    else:
        stopwords = set_stopwords(ad_appid, stopwords_lexicon_id)
    resource['lexicon_actrie'] = syn_actrie
    resource['stopwords'] = stopwords
    return resource


# 对query进行同义词扩展分词部分
async def query_syn_expansion(actrie, query, stopwords, dropped_words):
    # async def cal_queries(actrie, query, stopwords, dropped_words):
    # 从actrie获取同义词
    if actrie is None:
        std_mentions = []
    else:
        # 遍历 `actrie.iter_long(...)` 返回的每个匹配项 `index_value_tuple`，形如 (end_index, value)
        # 对每个匹配项生成一个新的元组 `(start_index, end_index, value)`，
        std_mentions = [
            (index_value_tuple[0] + 1 - len(index_value_tuple[1][0]), index_value_tuple[0] + 1, index_value_tuple[1])
            for index_value_tuple in
            actrie.iter_long(query.lower().replace(' ', ''))]
    # logger.debug(f'std_mentions =  {std_mentions}')
    syn2src2syns = {}
    for mention in std_mentions:
        for syn in mention[2]:
            syn = syn.lower().replace(' ', '')
            if syn in dropped_words:
                continue
            if syn not in syn2src2syns:
                syn2src2syns[syn] = {}
            syn2src2syns[syn][mention[2][0]] = list(mention[2])
    # logger.debug(f'syn2src2syns =  {syn2src2syns}')
    #  用 sum() 来展平列表可读性差且性能不佳，改写成列表推导式：
    # all_syns = sum([list(mention[2]) for mention in std_mentions], [])
    all_syns = [item for mention in std_mentions for item in mention[2]]
    # logger.debug(f'all_syns =  {all_syns}')
    all_syns = list(set([x.lower().replace(' ', '') for x in all_syns]))
    # logger.debug(f'all_syns =  {all_syns}')
    all_syns = [x for x in all_syns if x not in dropped_words]
    # logger.debug(f'all_syns =  {all_syns}')
    # 改写query
    query_cuts = []
    q_add_syn = query
    slices = []
    last_end = 0
    for mention in std_mentions:
        slices.append(query[last_end:mention[0]])
        cur_cuts = jieba.lcut(query[last_end:mention[0]])
        for cur_cut in cur_cuts:
            if not cur_cut.strip():
                continue
            is_stopword = False
            if cur_cut in stopwords:
                is_stopword = True
            query_cuts.append({
                "source": cur_cut,
                "synonym": [],
                "is_stopword": is_stopword
            })
        last_end = mention[1]
        for syn in list(mention[2])[1:]:
            if syn in dropped_words:
                continue
            q_add_syn += ' ' + syn
        query_cuts.append({
            "source": list(mention[2])[0],
            "synonym": list(mention[2][1:]),
            "is_stopword": False
        })
    slices.append(query[last_end:])
    # try:
    #     cur_cuts = []
    #     body = {
    #         "analyzer": "hanlp_index",
    #         "text": query
    #     }
    #     # opensearch的分词接口已经不能用了， 直接用结巴分词的
    #     res = await ad_opensearch_connector_with_url('_analyze', body)
    #     # res = await ad_opensearch_connector(search_params.ad_appid, str(search_params.kg_id), body, entity_classes=["analyze"])
    #     # logger.debug("======================================", res)
    #     for i in res["tokens"]:
    #         cur_cuts.append(i["token"])
    # except Exception as e:
    #     logger.error(f'查询open search查询分词结果错误，用jieba分词结果，报错如下: {e}')
    #     cur_cuts = jieba.lcut(query[last_end:])
    logger.info(f'使用jieba分词...')
    cur_cuts = jieba.lcut(query[last_end:])
    for cur_cut in cur_cuts:
        if not cur_cut.strip():
            continue
        is_stopword = False
        if cur_cut in stopwords:
            is_stopword = True
        query_cuts.append({
            "source": cur_cut,
            "synonym": [],
            "is_stopword": is_stopword
        })
    queries = []

    def backtrack(std_mentions, i, q):
        if i >= len(std_mentions):
            queries.append(q + slices[i])
            return
        mention = std_mentions[i]
        syns = [x for x in mention[2] if x not in dropped_words]
        for syn in syns:
            backtrack(std_mentions, i + 1, q + slices[i] + syn)

    backtrack(std_mentions, 0, '')
    return queries, query_cuts, all_syns

# 对query进行分词, 用于字段召回
async def query_segment(query):
    query_seg_list = [q_cut.lower() for q_cut in jieba.cut(query, cut_all=False) if q_cut.lower().strip()]
    logger.info("query cut result {}".format(query_seg_list))
    stop_set = get_default_stop_words()
    query_seg_list = [q_word for q_word in query_seg_list if q_word not in stop_set]
    logger.info("off stop word query cut result {}".format(query_seg_list))
    return query_seg_list


# 关键词搜索
async def lexical_search(query, queries, all_syns, entity_types, data_params, search_params):
# async def search_by_keyword(query, queries, all_syns, entity_types, data_params, search_params):

    space_name = data_params['space_name']
    drop_indices_lexical = []
    # opensearch 搜索语句
    body = {
        "query": {
            "dis_max": {
                "queries": [
                    {"multi_match": {"query": q, "type": "most_fields"}} for q in queries
                ],
                "tie_breaker": 0.3
            }
        },
        "highlight": {
            "require_field_match": False,
            "fields": {
                "*": {}
            }
        },
        '_source': {"excludes": ['_vector768']},
        "from": 0,
        "size": int(settings.OS_KEY_NUM)
    }
    logger.info(f'关键词搜索返回结果数量限制 = {settings.OS_KEY_NUM}')
    start_time = time.time()
    # 同义词扩展后的所有 query 分词，用于后续的排序分计算
    queries_words = [list(jieba.cut(q.lower())) for q in queries]
    filtered_queries_words = []
    for q_words in queries_words:
        q_words_f = [word for word in q_words if
                     word.strip() and word not in data_params['stopwords'] and word not in data_params['dropped_words']]
        filtered_queries_words.append(q_words_f)
    queries_words = filtered_queries_words
    ents = [[]]
    ent_vids = [dic['vid'] for ent in ents for dic in ent if dic['graph_id'] == search_params.kg_id]
    ent_vids = set(ent_vids)
    end_time = time.time()
    query_segment_time = end_time - start_time
    logger.info(f"query分词 耗时 {query_segment_time} 秒")

    score_key_list = []
    hits_lexical = []
    hits_id_lexical = []
    '''关键词搜索'''
    # os_indices_list = []
    f_start_time = time.time()
    # for w, ent_group in data_params['weights_group']:
    #     os_indices = [space_name + '_' + tag.lower() for tag, weight in ent_group]
    #     os_indices_list += os_indices
    # url = ",".join(os_indices_list) + "/_search"
    # res = await ad_opensearch_connector(url, body)
    res = await ad_opensearch_connector(search_params.ad_appid, str(search_params.kg_id), body, entity_classes=["*"])
    if res.get('hits',{}).get('hits'):
        hits = res['hits']['hits']
    else:
        hits = {}
    f_end_time = time.time()
    query_segment_time = f_end_time - f_start_time
    logger.info(f"opensearch 关键词搜索耗时 {query_segment_time} 秒")
    logger.info(f'opensearch 关键词搜索召回数量 = {len(hits)}')

    g_start_time = time.time()
    for hit in hits:
        if hit:
            hits_id_lexical.append(hit['_id'])
            hits_lexical.append(hit)
    # 重新计算关键词排序分数
    for i, hit in enumerate(hits_lexical):
        start_synonyms = []
        max_prop_score = 0
        max_score_prop = ''
        hit_keywords = []
        score_class_out = []
        score_num_out = 0
        score_ratio_out = 0
        score = 0
        hit_num = 0
        matched = False
        hits_lexical[i]['os_score'] = hits_lexical[i]['_score']
        tag_lower = hit['_index'][len(space_name) + 1:]
        tag = data_params['indextag2tag'].get(tag_lower, tag_lower)
        default_prop = entity_types[tag]['default_tag']
        if tag in data_params['type2names'] and default_prop in hit['_source'] and hit['_source'][default_prop] in \
                data_params['type2names'][
                    tag]:
            drop_indices_lexical.append(hit["_id"])
            continue
        # 遍历这个实体点所有属性
        for prop, v in hit['highlight'].items():
            value = v[0]
            a = r'<em>(.*?)</em>'
            words = re.findall(a, value)
            for syn in all_syns:
                if syn in value:
                    start_synonyms.append(syn)
            # 记录匹配query比例，之后计算最大值
            score_class_in = 0
            # 匹配次数,之后加总
            score_num_in = 0
            # 计算分数
            score_ratio_in = 0
            # 遍历所有同义词query,取分数最大的query语句
            for q_words in queries_words:
                score_class_in, score_num_in, score_ratio_in = max(
                    (score_class_in, score_num_in, score_ratio_in),
                    lev_dis_score(q_words, words))
            if score_class_in > 0 or score_num_in > 0 or score_ratio_in > 0:
                matched = True
                hit_num += 1
                for value in set(sum(queries_words, [])).intersection(set(words)):
                    if value not in hit_keywords: hit_keywords.append(value)
            if not matched and value.strip() and value.lower() in query.lower() and value not in data_params[
                'stopwords'] + data_params['dropped_words']:
                matched = True
                score_ratio_in += len(value) / (len(query) + 0.01)
                max_score_prop = prop
                hit_keywords.append(value)
            if not matched and query.lower() in value.lower() and query not in data_params['stopwords'] + data_params[
                'dropped_words']:
                matched = True
                score_ratio_in += len(query) / (len(value) + 0.01)
                max_score_prop = prop
                hit_keywords.append(query)
            if score_ratio_in > max_prop_score and not max_score_prop:
                max_score_prop = prop
            # 所有属性的分数汇总
            score_class_out.append(score_class_in)
            score_num_out += score_num_in
            score_ratio_out += score_ratio_in
        # 计算这个实体点的分数
        if score_ratio_out > 0 or max(score_class_out) > 0 or score_num_out > 0:
            hits_lexical[i]['score_class'] = max(score_class_out)
            hits_lexical[i]['score_num'] = score_num_out
            hits_lexical[i]['score_ratio'] = score_ratio_out / (hit_num + 0.01)
            hits_lexical[i]['max_score_prop'] = {
                "prop": max_score_prop,
                "value": hit['_source'].get(max_score_prop, ''),
                "keys": hit_keywords
            }
            hits_lexical[i]['key_score'] = max(
                score_class_out) * 100000 + score_num_out * 10 + score_ratio_out / (hit_num + 0.01)
        else:
            hits_lexical[i]['key_score'] = hits_lexical[i]['os_score']
            hits_lexical[i]['max_score_prop'] = {
                "prop": '',
                "value": '',
                "keys": []
            }
        if hit['_id'] in ent_vids:
            score += 1
        hits_lexical[i]['start_synonyms'] = list(set(start_synonyms))
        score_key_list.append(hits_lexical[i]['key_score'])
    transfer = MinMaxScaler(feature_range=(0.8, 1))
    if len(score_key_list) == 0:
        pass
    else:
        score_key_list = np.array(score_key_list).reshape(-1, 1)
        data = transfer.fit_transform(score_key_list)
        for i, value in enumerate(data):
            hits_lexical[i]['_score'] = value[0]
    vid_hits_lexical = {hit['_id']: hit for hit in hits_lexical}
    g_end_time = time.time()
    calculate_score_time = g_end_time - g_start_time
    logger.info(f"关键词搜索 耗时 {calculate_score_time} 秒")
    # return hits_key_id, vid_hits_key, hits_key, drop_indices_key
    return hits_id_lexical, vid_hits_lexical, hits_lexical, drop_indices_lexical


async def lexical_search_dip(query, queries, all_syns, entity_types, data_params, search_params):
# async def search_by_keyword(query, queries, all_syns, entity_types, data_params, search_params):

    space_name = data_params['space_name']
    drop_indices_lexical = []
    # opensearch 搜索语句
    body = {
        "query": {
            "dis_max": {
                "queries": [
                    {"multi_match": {"query": q, "type": "most_fields"}} for q in queries
                ],
                "tie_breaker": 0.3
            }
        },
        "highlight": {
            "require_field_match": False,
            "fields": {
                "*": {}
            }
        },
        '_source': {"excludes": ['_vector768']},
        "from": 0,
        "size": int(settings.OS_KEY_NUM)
    }
    logger.info(f'关键词搜索返回结果数量限制 = {settings.OS_KEY_NUM}')
    start_time = time.time()
    # 同义词扩展后的所有 query 分词，用于后续的排序分计算
    queries_words = [list(jieba.cut(q.lower())) for q in queries]
    filtered_queries_words = []
    for q_words in queries_words:
        q_words_f = [word for word in q_words if
                     word.strip() and word not in data_params['stopwords'] and word not in data_params['dropped_words']]
        filtered_queries_words.append(q_words_f)
    queries_words = filtered_queries_words
    ents = [[]]
    ent_vids = [dic['vid'] for ent in ents for dic in ent if dic['graph_id'] == search_params.kg_id]
    ent_vids = set(ent_vids)
    end_time = time.time()
    query_segment_time = end_time - start_time
    logger.info(f"query分词 耗时 {query_segment_time} 秒")

    score_key_list = []
    hits_lexical = []
    hits_id_lexical = []
    '''关键词搜索'''
    # os_indices_list = []
    f_start_time = time.time()
    # for w, ent_group in data_params['weights_group']:
    #     os_indices = [space_name + '_' + tag.lower() for tag, weight in ent_group]
    #     os_indices_list += os_indices
    # url = ",".join(os_indices_list) + "/_search"
    # res = await ad_opensearch_connector(url, body)
    res = await ad_opensearch_connector_dip(
        x_account_id=search_params.subject_id,
        x_account_type=search_params.subject_type,
        kg_id=str(search_params.kg_id),
        params=body,
        entity_classes=["*"]
    )
    if res.get('hits',{}).get('hits'):
        hits = res['hits']['hits']
    else:
        hits = {}
    f_end_time = time.time()
    query_segment_time = f_end_time - f_start_time
    logger.info(f"opensearch 关键词搜索耗时 {query_segment_time} 秒")
    logger.info(f'opensearch 关键词搜索召回数量 = {len(hits)}')

    g_start_time = time.time()
    for hit in hits:
        if hit:
            hits_id_lexical.append(hit['_id'])
            hits_lexical.append(hit)
    # 重新计算关键词排序分数
    for i, hit in enumerate(hits_lexical):
        start_synonyms = []
        max_prop_score = 0
        max_score_prop = ''
        hit_keywords = []
        score_class_out = []
        score_num_out = 0
        score_ratio_out = 0
        score = 0
        hit_num = 0
        matched = False
        hits_lexical[i]['os_score'] = hits_lexical[i]['_score']
        tag_lower = hit['_index'][len(space_name) + 1:]
        tag = data_params['indextag2tag'].get(tag_lower, tag_lower)
        default_prop = entity_types[tag]['default_tag']
        if tag in data_params['type2names'] and default_prop in hit['_source'] and hit['_source'][default_prop] in \
                data_params['type2names'][
                    tag]:
            drop_indices_lexical.append(hit["_id"])
            continue
        # 遍历这个实体点所有属性
        for prop, v in hit['highlight'].items():
            value = v[0]
            a = r'<em>(.*?)</em>'
            words = re.findall(a, value)
            for syn in all_syns:
                if syn in value:
                    start_synonyms.append(syn)
            # 记录匹配query比例，之后计算最大值
            score_class_in = 0
            # 匹配次数,之后加总
            score_num_in = 0
            # 计算分数
            score_ratio_in = 0
            # 遍历所有同义词query,取分数最大的query语句
            for q_words in queries_words:
                score_class_in, score_num_in, score_ratio_in = max(
                    (score_class_in, score_num_in, score_ratio_in), lev_dis_score(q_words, words)
                )
            if score_class_in > 0 or score_num_in > 0 or score_ratio_in > 0:
                matched = True
                hit_num += 1
                for value in set(sum(queries_words, [])).intersection(set(words)):
                    if value not in hit_keywords: hit_keywords.append(value)
            if not matched and value.strip() and value.lower() in query.lower() and value not in data_params[
                'stopwords'] + data_params['dropped_words']:
                matched = True
                score_ratio_in += len(value) / (len(query) + 0.01)
                max_score_prop = prop
                hit_keywords.append(value)
            if not matched and query.lower() in value.lower() and query not in data_params['stopwords'] + data_params[
                'dropped_words']:
                matched = True
                score_ratio_in += len(query) / (len(value) + 0.01)
                max_score_prop = prop
                hit_keywords.append(query)
            if score_ratio_in > max_prop_score and not max_score_prop:
                max_score_prop = prop
            # 所有属性的分数汇总
            score_class_out.append(score_class_in)
            score_num_out += score_num_in
            score_ratio_out += score_ratio_in
        # 计算这个实体点的分数
        if score_ratio_out > 0 or max(score_class_out) > 0 or score_num_out > 0:
            hits_lexical[i]['score_class'] = max(score_class_out)
            hits_lexical[i]['score_num'] = score_num_out
            hits_lexical[i]['score_ratio'] = score_ratio_out / (hit_num + 0.01)
            hits_lexical[i]['max_score_prop'] = {
                "prop": max_score_prop,
                "value": hit['_source'].get(max_score_prop, ''),
                "keys": hit_keywords
            }
            hits_lexical[i]['key_score'] = max(
                score_class_out) * 100000 + score_num_out * 10 + score_ratio_out / (hit_num + 0.01)
        else:
            hits_lexical[i]['key_score'] = hits_lexical[i]['os_score']
            hits_lexical[i]['max_score_prop'] = {
                "prop": '',
                "value": '',
                "keys": []
            }
        if hit['_id'] in ent_vids:
            score += 1
        hits_lexical[i]['start_synonyms'] = list(set(start_synonyms))
        score_key_list.append(hits_lexical[i]['key_score'])
    transfer = MinMaxScaler(feature_range=(0.8, 1))
    if len(score_key_list) == 0:
        pass
    else:
        score_key_list = np.array(score_key_list).reshape(-1, 1)
        data = transfer.fit_transform(
            X=score_key_list
        )
        for i, value in enumerate(data):
            hits_lexical[i]['_score'] = value[0]
    vid_hits_lexical = {hit['_id']: hit for hit in hits_lexical}
    g_end_time = time.time()
    calculate_score_time = g_end_time - g_start_time
    logger.info(f"关键词搜索 耗时 {calculate_score_time} 秒")
    # return hits_key_id, vid_hits_key, hits_key, drop_indices_key
    return hits_id_lexical, vid_hits_lexical, hits_lexical, drop_indices_lexical

# query embedding向量化
# @async_timed()
async def query_m3e(query):
    if settings.ML_EMBEDDING_URL == '':
        logger.info(f"未获取到m3e向量服务地址")
        return [], -1
    em_start_time = time.time()
    logger.info(f'query embedding： query = {query}')
    embeddings, m_status = await m3e_embeddings(texts=query)
    em_end_time = time.time()
    em_score_time = em_end_time - em_start_time
    logger.info(f"query embedding 耗时 {em_score_time} 秒")
    return embeddings, m_status


# 向量搜索
# @async_timed()
async def vector_search(
        embeddings: List[str],
        m_status: int,
        vector_index_filed: dict[str, Any],
        entity_types: dict,
        data_params: dict,
        min_score: float,
        search_params: BaseModel,
        vec_knn_k: int = 50
):
    """
    Performs a vector search based on the provided embeddings and other parameters. The function
    adjusts its behavior according to the version of AD (Application Data) and searches for the
    nearest neighbors in the specified vector index fields, returning the hits that match the
    search criteria.

    Args:
        embeddings: A list of strings representing the embeddings for which to find the nearest
            neighbors.
        m_status: An integer indicating the status of the vector service; 0 if available, otherwise
            not available.
        vector_index_filed: A dictionary where keys are related to space names and values are lists
            of vector field names.
        entity_types: A dictionary containing information about different entity types.
        data_params: A dictionary with additional parameters such as space name and mappings from
            index tags to actual tags.
        min_score: A float representing the minimum score threshold for the search results.
        search_params: An instance of BaseModel containing the necessary parameters for the
            search, including app ID and knowledge graph ID.
        vec_knn_k: An optional integer specifying the number of nearest neighbors to return,
            default is 50.

    Returns:
        A tuple containing two elements:
            - The first element is a list of dictionaries, each representing a hit from the
              vector search, excluding those marked for dropping.
            - The second element is a list of IDs corresponding to the hits that were marked
              for dropping based on certain criteria.

    Raises:
        Exception: If there is an issue during the execution, such as a failure in connecting
            to the OpenSearch service or processing the response.
    """
    space_name = data_params['space_name']
    '''纯向量搜索'''
    drop_indices_vec = []
    hits_vec = []
    vec_ids = []
    query = ''
    logger.info(f'认知搜索图谱向量搜索返回结果数量限制 = {settings.OS_VEC_NUM}')
    # logger.info(f'认知搜索图谱向量搜索返回结果数量限制 = {search_configs.sailor_vec_size_analysis_search}')
    # logger.info('AD版本是{}'.format(settings.AD_VERSION))

    # logger.debug(f'"min_score": {min_score}')
    # logger.debug(f'\'k\': vec_knn_k')
    # 如果向量服务可用
    if m_status == 0:
        logger.info('query embedding success！')
        op_start_time = time.time()
        hits = []

        # 如果AD版本大于等于3.0.0.6, AD opensearch 向量字段索引都合并为一个名为'_vector768'的属性字段
        if int(str(settings.AD_VERSION).replace('.', '')) >= 3006:
            # `'k': 50` 参数用于指定K近邻（K-Nearest Neighbors, KNN）搜索时返回的最近邻居数量
            # 即- 从 `_vector768.vec` 字段中找到与提供的 `embeddings` 向量最相似的50个文档。

            opensearch_query_statement = {
                "size": int(settings.OS_VEC_NUM),  # 返回的文档总数
                "min_score": min_score,  # 最小得分
                '_source': {"excludes": ['_vector768']},
                "query": {
                    'nested': {
                        "path": '_vector768',
                        "query": {
                            "knn": {
                                '_vector768.vec': {
                                    "vector": embeddings,'k': vec_knn_k  # 返回最接近的 k 个向量
                                }
                            }
                        }
                    }

                }
            }
            # res = await ad_opensearch_connector_with_url(url=f'{space_name}_*/_search', body=query)
            logger.info(f'ad_opensearch_connector_dip running!')
            res = await ad_opensearch_connector_dip(x_account_id=search_params.subject_id,
                                                    x_account_type=search_params.subject_type,
                                                    kg_id=(search_params.kg_id),
                                                    params=opensearch_query_statement,
                                                    entity_classes=["*"])
            if res['hits']['hits']:
                hits += res['hits']['hits']
            else:
                pass
        # 如果AD版本小于等于3.0.0.5
        else:
            for k, value in vector_index_filed.items():
                vector_index = space_name + '_' + k
                for name in value:
                    vector_field = name + '-vector'
                    query += '{"index": "%s"}\n' % vector_index
                    query_module = {
                        "size": int(settings.OS_VEC_NUM) / 10,
                        "min_score": min_score + 1,
                        "query": {
                            "script_score": {
                                "query": {
                                    "match_all": {}
                                },
                                "script": {
                                    "source": "knn_score",
                                    "lang": "knn",
                                    "params": {
                                        "field": vector_field,
                                        "query_value": embeddings,
                                        "space_type": "cosinesimil"
                                    }
                                }
                            }
                        }
                    }
                    query += json.dumps(query_module)
                    query += "\n"
            # res = await ad_opensearch_connector_with_url(url=f'{space_name}/_msearch', body=query)
            res = await ad_opensearch_connector(search_params.ad_appid, str(search_params.kg_id), query,
                                                entity_classes=["*"])
            response = res.get('responses')
            for res in response:
                if res['hits']['hits']:
                    hits += res['hits']['hits']
                else:
                    pass

        op_end_time = time.time()
        op_score_time = op_end_time - op_start_time
        logger.info(f"认知搜索图谱向量搜索 耗时 {op_score_time} 秒")
        # 以上向量搜索是所有实体点都会搜索， 搜索结果 hits 包含了所有类型的实体点
        # logger.debug(f'hits={hits}')
        logger.info(f'认知搜索图谱向量搜索召回数量（未按照搜索列表或问答部分所需的实体类型 entity_types 筛选之前） = {len(hits)}')
        # logger.debug(f'hits = \n{hits}')
        # hits是向量搜索的结果
        for hit in hits:
            # logger.debug(f'hit = \n{hit}')
            # 从索引名称中提取实体类型名,即tag
            tag_lower = hit['_index'][len(space_name) + 1:]
            # logger.debug(f'tag_lower = {tag_lower}')
            # 如果 `tag_lower` 不在字典中，则返回以上 `tag_lower` 。
            tag = data_params['indextag2tag'].get(tag_lower, tag_lower)
            # logger.debug(f'tag = {tag}')
            # logger.debug(f'entity_types.keys() = {entity_types.keys()}')
            # logger.debug(f'tag in entity_types.keys() = {tag in entity_types.keys()}')
            if tag in entity_types.keys():
                # default_tag 是 实体类的默认字段(图谱中的显示名称),比如 resource 实体类的 default_tag 是 resourcename,
                # logger.debug(f"""entity_types[tag]['default_tag'] = {entity_types[tag]['default_tag']}""")
                default_prop = entity_types[tag]['default_tag']
                # type2names 字典 是前端传来的停用实体,现在已经废弃
                # drop_indices_vec是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
                # "_id"的值比如, "_id": "5e8ca9f378d62d55130a9cdc0f5be596",
                # logger.debug(f'before vec_ids = {vec_ids}')
                if (tag in data_params['type2names']
                        and default_prop in hit['_source']
                        and hit['_source'][default_prop] in data_params['type2names'][tag]):
                    drop_indices_vec.append(hit["_id"])
                    continue
                if hit["_id"] in vec_ids:
                    pass
                else:
                    vec_ids.append(hit["_id"])
                    hits_vec.append(hit)
                # logger.debug(f'after vec_ids = {vec_ids}')
                # logger.debug(f'hits_vec = {hits_vec}')
            else:
                pass
    else:
        logger.info(f"认知搜索图谱向量搜索不可用")
    # drop_indices_vec是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
    # hits_vec:list, drop_indices_vec:list
    return hits_vec, drop_indices_vec
    # hits_vec 是一个列表, 每一个元素 是搜索命中的相似向量对应的res['hits']['hits']部分(列表)的一个元素,示例数据如下


async def vector_search_dip(embeddings: List[str], m_status: int, vector_index_filed: dict[str, Any],
                            entity_types: dict,
                            data_params: dict, min_score: float, search_params: BaseModel, vec_knn_k: int = 50):
    """
    Performs a vector search based on the provided embeddings and other parameters. The function
    adjusts its behavior according to the version of AD (Application Data) and searches for the
    nearest neighbors in the specified vector index fields, returning the hits that match the
    search criteria.

    Args:
        embeddings: A list of strings representing the embeddings for which to find the nearest
            neighbors.
        m_status: An integer indicating the status of the vector service; 0 if available, otherwise
            not available.
        vector_index_filed: A dictionary where keys are related to space names and values are lists
            of vector field names.
        entity_types: A dictionary containing information about different entity types.
        data_params: A dictionary with additional parameters such as space name and mappings from
            index tags to actual tags.
        min_score: A float representing the minimum score threshold for the search results.
        search_params: An instance of BaseModel containing the necessary parameters for the
            search, including app ID and knowledge graph ID.
        vec_knn_k: An optional integer specifying the number of nearest neighbors to return,
            default is 50.

    Returns:
        A tuple containing two elements:
            - The first element is a list of dictionaries, each representing a hit from the
              vector search, excluding those marked for dropping.
            - The second element is a list of IDs corresponding to the hits that were marked
              for dropping based on certain criteria.

    Raises:
        Exception: If there is an issue during the execution, such as a failure in connecting
            to the OpenSearch service or processing the response.
    """
    space_name = data_params['space_name']
    '''纯向量搜索'''
    drop_indices_vec = []
    hits_vec = []
    vec_ids = []
    query = ''
    logger.info(f'认知搜索图谱向量搜索返回结果数量限制 = {settings.OS_VEC_NUM}')
    # logger.info(f'认知搜索图谱向量搜索返回结果数量限制 = {search_configs.sailor_vec_size_analysis_search}')
    # logger.info('AD版本是{}'.format(settings.AD_VERSION))

    # logger.debug(f'"min_score": {min_score}')
    # logger.debug(f'\'k\': vec_knn_k')
    # 如果向量服务可用
    if m_status == 0:
        logger.info('query embedding success！')
        op_start_time = time.time()
        hits = []

        # 如果AD版本大于等于3.0.0.6, AD opensearch 向量字段索引都合并为一个名为'_vector768'的属性字段

        # `'k': 50` 参数用于指定K近邻（K-Nearest Neighbors, KNN）搜索时返回的最近邻居数量
        # 即- 从 `_vector768.vec` 字段中找到与提供的 `embeddings` 向量最相似的50个文档。

        opensearch_query_statement = {
            "size": int(settings.OS_VEC_NUM),  # 返回的文档总数
            "min_score": min_score,  # 最小得分
            '_source': {"excludes": ['_vector768']},
            "query": {
                'nested': {
                    "path": '_vector768',
                    "query": {
                        "knn": {
                            '_vector768.vec': {
                                "vector": embeddings,
                                'k': vec_knn_k  # 返回最接近的 k 个向量
                            }
                        }
                    }
                }

            }
        }
        # res = await ad_opensearch_connector_with_url(url=f'{space_name}_*/_search', body=query)
        logger.info(f'ad_opensearch_connector_dip running!')
        res = await ad_opensearch_connector_dip(
            x_account_id=search_params.subject_id,
            x_account_type=search_params.subject_type,
            kg_id=search_params.kg_id,
            params=opensearch_query_statement,
            entity_classes=["*"]
        )
        if res['hits']['hits']:
            hits += res['hits']['hits']
        else:
            pass

        op_end_time = time.time()
        op_score_time = op_end_time - op_start_time
        logger.info(f"认知搜索图谱向量搜索 耗时 {op_score_time} 秒")
        # 以上向量搜索是所有实体点都会搜索， 搜索结果 hits 包含了所有类型的实体点
        # logger.debug(f'hits={hits}')
        logger.info(f'认知搜索图谱向量搜索召回数量（未按照搜索列表或问答部分所需的实体类型 entity_types 筛选之前） = {len(hits)}')
        # logger.debug(f'hits = \n{hits}')
        # hits是向量搜索的结果
        for hit in hits:
            # logger.debug(f'hit = \n{hit}')
            # 从索引名称中提取实体类型名,即tag
            tag_lower = hit['_index'][len(space_name) + 1:]
            # logger.debug(f'tag_lower = {tag_lower}')
            # 如果 `tag_lower` 不在字典中，则返回以上 `tag_lower` 。
            tag = data_params['indextag2tag'].get(tag_lower, tag_lower)
            # logger.debug(f'tag = {tag}')
            # logger.debug(f'entity_types.keys() = {entity_types.keys()}')
            # logger.debug(f'tag in entity_types.keys() = {tag in entity_types.keys()}')
            if tag in entity_types.keys():
                # default_tag 是 实体类的默认字段(图谱中的显示名称),比如 resource 实体类的 default_tag 是 resourcename,
                # logger.debug(f"""entity_types[tag]['default_tag'] = {entity_types[tag]['default_tag']}""")
                default_prop = entity_types[tag]['default_tag']
                # type2names 字典 是前端传来的停用实体,现在已经废弃
                # drop_indices_vec是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
                # "_id"的值比如, "_id": "5e8ca9f378d62d55130a9cdc0f5be596",
                # logger.debug(f'before vec_ids = {vec_ids}')
                if (tag in data_params['type2names']
                        and default_prop in hit['_source']
                        and hit['_source'][default_prop] in data_params['type2names'][tag]):
                    drop_indices_vec.append(hit["_id"])
                    continue
                if hit["_id"] in vec_ids:
                    pass
                else:
                    vec_ids.append(hit["_id"])
                    hits_vec.append(hit)
                # logger.debug(f'after vec_ids = {vec_ids}')
                # logger.debug(f'hits_vec = {hits_vec}')
            else:
                pass
    else:
        logger.info(f"认知搜索图谱向量搜索不可用")
    # drop_indices_vec是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
    # hits_vec:list, drop_indices_vec:list
    return hits_vec, drop_indices_vec
    # hits_vec 是一个列表, 每一个元素 是搜索命中的相似向量对应的res['hits']['hits']部分(列表)的一个元素,示例数据如下


async def vector_search_dip_new(
        headers,
        vector_index_filed: dict[str, Any],
        entity_types: dict,
        data_params: dict,
        min_score: float,
        search_params: BaseModel,
        vec_knn_k: int = 50
):
    """
    """
    # space_name = data_params['space_name']
    '''纯向量搜索'''
    drop_indices_vec = []
    hits_vec = []
    vec_ids = []
    query = ''
    logger.info(f'认知搜索图谱向量搜索返回结果数量限制 = {settings.OS_VEC_NUM}')
    # logger.debug(f'"min_score": {min_score}')
    # logger.debug(f'\'k\': vec_knn_k')

    op_start_time = time.time()
    hits = []

    # `'k': 50` 参数用于指定K近邻（K-Nearest Neighbors, KNN）搜索时返回的最近邻居数量
    # 即- 从 `_vector768.vec` 字段中找到与提供的 `embeddings` 向量最相似的50个文档。

    # 搜索中间点，数据资源或数据资源目录中所有建了向量索引的字段

    tasks = []
    for class_id, value in vector_index_filed.items():
        # vec_search_statement=None
        sub_conditions = []
        for vector_field in value:

            sub_condition={
                            "field": vector_field,
                            "operation": "knn",
                            "value": search_params.query,
                            "limit_key": "k",
                            "limit_value": 10
                        }
            sub_conditions.append(sub_condition)
            logger.info(f'sub_condition = {sub_condition}')

        vec_search_statement = {
            "condition": {
                "operation": "or",
                "sub_conditions": sub_conditions
            },
            "limit": int(int(settings.OS_VEC_NUM) / 10),
            "need_total": True
        }
        logger.info(f'vec_search_statement = {vec_search_statement}')

        # task = asyncio.create_task(
        #     find_number_api.dip_ontology_query_by_object_types(
        #         kn_id=search_params.kg_id,
        #         class_id=class_id,
        #         body=vec_search_statement,
        #         x_account_id=search_params.subject_id,
        #         x_account_type=search_params.subject_type
        #     )
        # )
        # 改为外部接口调用
        task = asyncio.create_task(
            find_number_api.dip_ontology_query_by_object_types_external(
                token=headers.get("Authorization"),
                kn_id=search_params.kg_id,
                class_id=class_id,
                body=vec_search_statement
            )
        )
        tasks.append(task)

    res_list = await asyncio.gather(*tasks)

    # res = await find_number_api.dip_ontology_query_by_object_types(
    #     kn_id=search_params.kg_id,
    #     class_id=class_id,
    #     body=vec_search_statement,
    #     x_account_id=search_params.subject_id,
    #     x_account_type=search_params.subject_type
    # )
    logger.info(f'res of dip_ontology_query_by_object_types() res_list ={res_list}')
    # new_list = []
    # 要将dip的数据结构转换为 原AD hit 数据结构
    for res in res_list:
        class_id = res[0]  # 元组中的第一项
        datas = res[1]['datas']  # datas 列表

        for data in datas:
            # 提取 _score
            score = data['_score']

            # 创建 _source 字典，排除 _score 字段
            source = {k: v for k, v in data.items() if k != '_score'}

            # 构建新字典
            new_item = {
                "class_id": class_id,
                "_score": score,
                "_source": source
            }

            hits.append(new_item)

    # response = res.get('responses')
    # for res in response:
    #     if res['hits']['hits']:
    #         hits += res['hits']['hits']
    #     else:
    #         pass
    #
    # if res['hits']['hits']:
    #     hits += res['hits']['hits']
    # else:
    #     pass

    op_end_time = time.time()
    op_score_time = op_end_time - op_start_time
    logger.info(f"认知搜索图谱向量搜索 耗时 {op_score_time} 秒")
    # 以上向量搜索是所有实体点都会搜索， 搜索结果 hits 包含了所有类型的实体点
    # logger.debug(f'hits={hits}')
    logger.info(f'认知搜索图谱向量搜索召回数量（未按照搜索列表或问答部分所需的实体类型 entity_types 筛选之前） = {len(hits)}')
    # logger.debug(f'hits = \n{hits}')
    # hits是向量搜索的结果
    for hit in hits:
        # logger.debug(f'hit = \n{hit}')
        # 从索引名称中提取实体类型名,即tag
        # tag_lower = hit['_index'][len(space_name) + 1:]
        tag_lower = hit['class_id']
        # logger.debug(f'tag_lower = {tag_lower}')
        # 如果 `tag_lower` 不在字典中，则返回以上 `tag_lower` 。
        tag = data_params['indextag2tag'].get(tag_lower, tag_lower)
        # logger.debug(f'tag = {tag}')
        # logger.debug(f'entity_types.keys() = {entity_types.keys()}')
        # logger.debug(f'tag in entity_types.keys() = {tag in entity_types.keys()}')
        if tag in entity_types.keys():
            # default_tag 是 实体类的默认字段(图谱中的显示名称),比如 resource 实体类的 default_tag 是 resourcename,
            # logger.debug(f"""entity_types[tag]['default_tag'] = {entity_types[tag]['default_tag']}""")
            default_prop = entity_types[tag]['default_tag']
            # type2names 字典 是前端传来的停用实体,现在已经废弃
            # drop_indices_vec是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
            # "_id"的值比如, "_id": "5e8ca9f378d62d55130a9cdc0f5be596",
            # logger.debug(f'before vec_ids = {vec_ids}')
            # if (tag in data_params['type2names']
            #         and default_prop in hit['_source']
            #         and hit['_source'][default_prop] in data_params['type2names'][tag]):
            #     drop_indices_vec.append(hit["_id"])
            #     continue
            # if hit["_id"] in vec_ids:
            #     pass
            # else:
            #     vec_ids.append(hit["_id"])
            #     hits_vec.append(hit)
            hits_vec.append(hit)
            # logger.debug(f'after vec_ids = {vec_ids}')
            # logger.debug(f'hits_vec = {hits_vec}')
        else:
            pass

    # drop_indices_vec是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
    # hits_vec:list, drop_indices_vec:list
    return hits_vec
    # hits_vec 是一个列表, 每一个元素 是搜索命中的相似向量对应的res['hits']['hits']部分(列表)的一个元素,示例数据如下

async def vector_search_kecc(ad_appid, kg_id_kecc, query_embedding, m_status, vector_index_filed, entity_types,
                             data_params, vec_size_kecc, vec_min_score_kecc, vec_knn_k_kecc):
    """
    Performs a vector search in an OpenSearch index for a given query embedding. The function supports different versions of the AD (Application Directory) and adjusts its behavior based on the version. It constructs a query to find the most similar vectors to the provided embedding and returns the matching entities.

    """
    space_name = data_params['space_name']
    logger.info(f"space_name = {space_name}")
    '''纯向量搜索'''
    # drop_indices_vec = []
    all_hits_entity = []
    vec_ids = []
    query = ''
    logger.info(f'部门职责知识增强图谱向量搜索返回结果数量限制 = {vec_size_kecc}')
    logger.info('AD版本是{}'.format(settings.AD_VERSION))
    # 如果向量服务可用
    if m_status == 0:
        op_start_time = time.time()
        hits = []
        logger.info('query embedding success！')
        # 如果AD版本大于等于3.0.0.6, 向量字段索引都合并为一个名为'_vector768'的
        if int(str(settings.AD_VERSION).replace('.', '')) >= 3006:
            # `'k': 50` 参数用于指定K近邻（K-Nearest Neighbors, KNN）搜索时返回的最近邻居数量
            # 即- 从 `_vector768.vec` 字段中找到与提供的 `embeddings` 向量最相似的50个文档。
            # `size`：控制返回结果的最大数量。
            # `k`应>=`size`: 如果你设置了 `k` 为 50，但 `size` 为 100，那么实际上返回的结果数量将由 `k` 决定，
            # 即最多 50 个文档。在这种情况下，增加 `size` 对性能的影响较小，因为实际返回的文档数量仍然由 `k` 控制。
            # `min_score`：设置一个得分阈值，过滤掉得分低于该阈值的文档。
            query = {
                "size": vec_size_kecc,  # 返回的文档总数
                "min_score": vec_min_score_kecc,  # 最小得分
                '_source': {"excludes": ['_vector768']},
                "query": {
                    'nested': {
                        "path": '_vector768',
                        "query": {
                            "knn": {
                                '_vector768.vec': {
                                    "vector": query_embedding,
                                    'k': vec_knn_k_kecc  # 返回最接近的50个向量
                                }
                            }
                        }
                    }

                }
            }
            # res = await ad_opensearch_connector_with_url(url=f'{space_name}_*/_search', body=query)
            res = await ad_opensearch_connector(ad_appid, str(kg_id_kecc), query, entity_classes=["*"])
            if res['hits']['hits']:
                hits += res['hits']['hits']
            else:
                pass
        # 如果AD版本小于等于3.0.0.5
        else:
            for k, value in vector_index_filed.items():
                vector_index = space_name + '_' + k
                for name in value:
                    vector_field = name + '-vector'
                    query += '{"index": "%s"}\n' % vector_index
                    query_module = {
                        "size": int(settings.OS_VEC_NUM) / 10,
                        "min_score": vec_min_score_kecc + 1,
                        "query": {
                            "script_score": {
                                "query": {
                                    "match_all": {}
                                },
                                "script": {
                                    "source": "knn_score",
                                    "lang": "knn",
                                    "params": {
                                        "field": vector_field,
                                        "query_value": query_embedding,
                                        "space_type": "cosinesimil"
                                    }
                                }
                            }
                        }
                    }
                    query += json.dumps(query_module)
                    query += "\n"
            # res = await ad_opensearch_connector_with_url(url=f'{space_name}/_msearch', body=query)
            res = await ad_opensearch_connector(ad_appid, str(kg_id_kecc), query,
                                                entity_classes=["*"])
            response = res.get('responses')
            for res in response:
                if res['hits']['hits']:
                    hits += res['hits']['hits']
                else:
                    pass

        op_end_time = time.time()
        op_score_time = op_end_time - op_start_time
        logger.info(f"部门职责知识增强图谱向量搜索 耗时 {op_score_time} 秒")
        logger.info(f'部门职责知识增强图谱向量搜索召回数量 = {len(hits)}')
        # hits是向量搜索的结果
        for hit in hits:
            # 从索引名称中提取实体类型名,即tag
            # logger.debug("hit=", hit)
            tag_lower = hit['_index'][len(space_name) + 1:]
            # logger.debug("tag_lower=",tag_lower)
            #     - 如果 `tag_lower` 不在字典中，则返回以上 `tag_lower` 。
            # data_params['indextag2tag',目前还没有这个字段
            # tag = data_params['indextag2tag'].get(tag_lower, tag_lower)
            tag = tag_lower
            # logger.debug("tag=", tag)
            # logger.debug("entity_types.keys()=", entity_types.keys())
            if tag in entity_types.keys():
                # default_tag 是 实体类的默认字段(图谱中的显示名称),比如resource实体类的default_tag是 resourcename,
                # default_prop = entity_types[tag]['default_tag']
                # type2names 字典 是前端传来的停用实体,现在已经废弃
                # drop_indices_vec是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
                # if tag in data_params['type2names'] and default_prop in i['_source'] and i['_source'][default_prop] in data_params['type2names'][tag]:
                #     drop_indices_vec.append(i["_id"])
                #     continue
                # logger.debug("vec_ids=", vec_ids)
                # logger.debug("all_hits_entity=", all_hits_entity)
                if hit["_id"] in vec_ids:
                    pass
                else:
                    vec_ids.append(hit["_id"])
                    all_hits_entity.append(hit)
            else:
                pass
    else:
        logger.info(f"部门职责知识增强图谱向量搜索不可用")
    # hits_vec 是搜索命中的相似向量对应的实体id
    # drop_indices_vec是按照停用实体信息,应该被过滤掉的向量,现在已经废弃
    # return hits_vec, drop_indices_vec
    # logger.debug("=all_hits_entity", all_hits_entity)
    return all_hits_entity
    # all_hits_entity 是一个列表, 每一个元素 是搜索命中的相似向量对应的res['hits']['hits']部分(列表)的一个元素

# 调用图分析函数
# async def fetch(kg_id, ad_appid, params):
async def custom_graph_call(kg_id, ad_appid, params):
    s_res = await prompt_svc.custom_search_graph_call(kg_id, ad_appid, params)
    if s_res is not None and 'res' in s_res.keys():
        s_res = s_res['res'][0]
        return s_res
    else:
        return None


async def custom_graph_call_dip(x_account_id, x_account_type, kg_id, params):
    s_res = await custom_search_graph_call_dip(
        x_account_id=x_account_id,
        x_account_type=x_account_type,
        kg_id=kg_id,
        params=params
    )
    if s_res is not None and 'res' in s_res.keys():
        s_res = s_res['res'][0]
        return s_res
    else:
        return None

# 调用大模型
# prompt_name 是提示词模版的名称
# table_name 是前一步查询知识库得到的所有候选表名,调用大模型的时候没有用到, 是在解析大模型返回结果的时候用到的
# 数据资源版中, table_name是形如 'table_name','interface_name','indicator_name'这样的字符串,
# 用于区分不同的数据资源: 逻辑视图/接口服务/指标
async def qw_gpt(data, query, appid, prompt_name, table_name):
    list_catalog = []
    list_catalog_reason = ''
    start1 = time.ctime()
    start = time.time()
    ad = PromptServices()
    # prompt_data 是提示词模版中的变量
    prompt_data = {'data_dict': str(data), 'query': query}
    # prompt_id 是AD模型工厂中提示词模版的id
    _, prompt_id = await ad.from_anydata(appid, prompt_name)
    logger.info(f"prompt_data = {prompt_data}")
    logger.info(f"prompt_id = {prompt_id}")
    try:
        # 调用大模型,
        res = await find_number_api.exec_prompt_by_llm(prompt_data, appid, prompt_id)
    except Exception as e:
        logger.error(f'调用大模型出错，报错信息如下: {e}')
        res = " "
    if res:
        logger.info(f'大模型调用返回结果 = {res}')
        # sp是大模型返回结果中的json部分
        sp = res.split("```")
        if len(sp) > 1:
            if sp[1][:4] == 'json':
                a = sp[1][4:]
            else:
                a = sp[1]
            try:
                # res_json 是大模型返回结果中的json部分
                res_json = json.loads(a)
            except:
                res_json = {}
            if "推荐实例" in res_json:
                for i in res_json["推荐实例"]:
                    #  list_catalog 是资源名称, 从res_json中拆出来的
                    list_catalog.append(i[table_name])
            if "分析步骤" in res_json:
                list_catalog_reason = res_json["分析步骤"]
        else:
            res_json = {}
        end1 = time.ctime()
        end = time.time()
        logger.info(f'开始时间 = {start1}, 结束时间 = {end1}, 调用大模型耗时 = {end - start}')
        # logger.debug('大模型整理结果', list_catalog, list_catalog_reason,res_json)
        # res_json 是大模型原始返回结果
        # list_catalog 是资源名称, 从res_json中拆出来的
        # list_catalog_reason是分析思路话术, 从res_json中拆出来的
        logger.info(
            f'大模型返回结果整理后: \nlist_catalog = {list_catalog}\nlist_catalog_reason = {list_catalog_reason}\nres_json = {res_json}')

        #
        return list_catalog, list_catalog_reason, res_json
    else:
        return [], '', {}

async def qw_gpt_dip(headers, data, query, search_configs, prompt_name, table_name):
    logger.info(f'qw_gpt_dip() running!')
    list_catalog = []
    list_catalog_reason = ''
    start1 = time.ctime()
    start = time.time()
    prompt_var_data = {'data_dict': str(data), 'query': query}
    logger.info(f"prompt_var_data = {prompt_var_data}")
    prompt_template = prompt_map.get(prompt_name, "")
    logger.info(f'prompt_tmplate = {prompt_template}')
    if prompt_template:
        prompt_rendered = prompt_template
        for prompt_var, value in prompt_var_data.items():
            logger.info(f'prompt_var = {prompt_var}, value = {value}')
            prompt_rendered = prompt_rendered.replace("{{" + str(prompt_var) + "}}", str(value))
            logger.info(f'prompt_rendered = {prompt_rendered}')
        prompt_rendered_msg = [
            {
                "role": "user",
                "content": prompt_rendered
            }
        ]
    else:
        raise Exception(f"prompt_template is None, prompt_name={prompt_name}")

    try:
        # 调用大模型,
        # res = await find_number_api.exec_prompt_by_llm_dip_private(
        #     prompt_rendered_msg=prompt_rendered_msg,
        #     search_configs=search_configs,
        #     x_account_id=x_account_id
        # )
        # 改成外部接口调用
        res = await find_number_api.exec_prompt_by_llm_dip_external(
            token=headers.get('Authorization'),
            prompt_rendered_msg=prompt_rendered_msg,
            search_configs=search_configs
        )

    except Exception as e:
        logger.error(f'调用大模型出错，报错信息如下: {e}')
        res = " "
    if res:
        logger.info(f'大模型调用返回结果 = {res}')
        # sp是大模型返回结果中的json部分
        sp = res.split("```")
        if len(sp) > 1:
            if sp[1][:4] == 'json':
                a = sp[1][4:]
            else:
                a = sp[1]
            try:
                # res_json 是大模型返回结果中的json部分
                res_json = json.loads(a)
            except:
                res_json = {}
            if "推荐实例" in res_json:
                for i in res_json["推荐实例"]:
                    #  list_catalog 是资源名称, 从res_json中拆出来的
                    list_catalog.append(i[table_name])
            if "分析步骤" in res_json:
                list_catalog_reason = res_json["分析步骤"]
        else:
            res_json = {}
        end1 = time.ctime()
        end = time.time()
        logger.info(f'开始时间 = {start1}, 结束时间 = {end1}, 调用大模型耗时 = {end - start}')
        # logger.debug('大模型整理结果', list_catalog, list_catalog_reason,res_json)
        # res_json 是大模型原始返回结果
        # list_catalog 是资源名称, 从res_json中拆出来的
        # list_catalog_reason是分析思路话术, 从res_json中拆出来的
        logger.info(
            f'大模型返回结果整理后: \nlist_catalog = {list_catalog}\nlist_catalog_reason = {list_catalog_reason}\nres_json = {res_json}')

        return list_catalog, list_catalog_reason, res_json
    else:
        return [], '', {}

# 2025.10.15 为报告生成工具用部门职责数据， 将”相关信息“单独解析出来
async def qw_gpt_kecc(data, query, dept_infosystem_duty, appid, prompt_name, table_name):
    list_catalog = []
    list_catalog_reason = ''
    related_info = []
    start1 = time.ctime()
    start = time.time()
    ad = PromptServices()
    data_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    dept_infosystem_duty_str = json.dumps(dept_infosystem_duty, ensure_ascii=False, separators=(',', ':'))
    # prompt_var_data 是提示词模版中的变量值
    prompt_var_data = {'data_dict': data_str, 'dept_infosystem_duty': dept_infosystem_duty_str, 'query': query}
    # prompt_data = {'data_dict': str(data), 'dept_infosystem_duty': dept_infosystem_duty, 'query': query}
    # prompt_id 是AD模型工厂中提示词模版的id
    _, prompt_id = await ad.from_anydata(appid, prompt_name)
    # logger.debug(prompt_data, prompt_id)
    try:
        # 调用大模型,
        res = await find_number_api.exec_prompt_by_llm(prompt_var_data, appid, prompt_id)
    except Exception as e:
        logger.info(f'调用大模型出错，报错信息如下: {e}')
        res = " "
    if res:
        logger.info(f'大模型调用返回结果 =  {res}')
        # sp是大模型返回结果中的json部分
        res_sp = res.split("```")
        # logger.debug(f"res_sp = {res_sp}")
        if len(res_sp) > 1:
            if res_sp[1][:4] == 'json':
                a = res_sp[1][4:]
            else:
                a = res_sp[1]
            # logger.debug(f"res_sp = {res_sp}")

            try:
                # res_json 是大模型返回结果中的json部分
                res_json = json.loads(a)
            except Exception as e:
                res_json = {}
                logger.info(f"json.loads error:{e}")
            # logger.debug(f"res_json={res_json}")
            if "推荐实例" in res_json:
                for i in res_json["推荐实例"]:
                    #  list_catalog 是资源名称, 从res_json中拆出来的
                    list_catalog.append(i[table_name])
                    # logger.debug(f"list_catalog={list_catalog}")
            if "分析步骤" in res_json:
                list_catalog_reason = res_json["分析步骤"]
                # logger.debug(f"list_catalog_reason={list_catalog_reason}")
            # 分析问答型搜索修改提示词后， 相关信息部分大模型输出的是一个json列表
            if "相关信息" in res_json:
                logger.info(f"res_json['相关信息'] = {res_json['相关信息']}")
                for j in res_json["相关信息"]:
                    related_info.append(j)
                    # logger.info(f'relatedd_info={related_info}')
                # if isinstance(res_json["相关信息"], str):
                #     list_catalog_reason = list_catalog_reason + '<br>' + res_json["相关信息"]
                # # 如果“相关信息”的值是列表，这里使用空格作为分隔符连接列表元素
                # elif isinstance(res_json["相关信息"], list):
                #     list_catalog_reason = list_catalog_reason + '<br>' + ' '.join(res_json["相关信息"])
                # else:
                #     # 对于其他类型的数据，尝试直接转换成字符串
                #     list_catalog_reason = list_catalog_reason + '<br>' + str(res_json["相关信息"])
                # # logger.debug(f"list_catalog_reason={list_catalog_reason}")

        else:
            res_json = {}
        end1 = time.ctime()
        end = time.time()
        logger.info(f'开始时间 = {start1}, 结束时间 = {end1}, 调用大模型耗时 = {end - start}')

        # res_json 是大模型原始返回结果的json部分, 要求大模型返回json形式
        # list_catalog 是资源名称, 从res_json中拆出来的
        # list_catalog_reason是分析思路话术, 从res_json中拆出来的
        # related_info 是部门职责数据， 单位-职责-信息系统
        logger.info(
            f'''大模型返回结果整理后: \nlist_catalog = {list_catalog}\nlist_catalog_reason = {list_catalog_reason}'
        related_info={related_info}\nres_json = {res_json}''')

        return list_catalog, list_catalog_reason, related_info, res_json
    else:
        return [], '', [], {}

async def qw_gpt_kecc_old(data, query, dept_infosystem_duty, appid, prompt_name, table_name):
    list_catalog = []
    list_catalog_reason = ''
    start1 = time.ctime()
    start = time.time()
    ad = PromptServices()
    data_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    dept_infosystem_duty_str = json.dumps(dept_infosystem_duty, ensure_ascii=False, separators=(',', ':'))
    # prompt_var_data 是提示词模版中的变量值
    prompt_var_data = {'data_dict': data_str, 'dept_infosystem_duty': dept_infosystem_duty_str, 'query': query}
    # prompt_data = {'data_dict': str(data), 'dept_infosystem_duty': dept_infosystem_duty, 'query': query}
    # prompt_id 是AD模型工厂中提示词模版的id
    _, prompt_id = await ad.from_anydata(appid, prompt_name)
    # logger.debug(prompt_data, prompt_id)
    try:
        # 调用大模型,
        res = await find_number_api.exec_prompt_by_llm(prompt_var_data, appid, prompt_id)
    except Exception as e:
        logger.info(f'调用大模型出错，报错信息如下: {e}')
        res = " "
    if res:
        logger.info(f'大模型调用返回结果 =  {res}')
        # sp是大模型返回结果中的json部分
        res_sp = res.split("```")
        # logger.debug(f"res_sp = {res_sp}")
        if len(res_sp) > 1:
            if res_sp[1][:4] == 'json':
                a = res_sp[1][4:]
            else:
                a = res_sp[1]
            # logger.debug(f"res_sp = {res_sp}")

            try:
                # res_json 是大模型返回结果中的json部分
                res_json = json.loads(a)
            except Exception as e:
                res_json = {}
                logger.info(f"json.loads error:{e}")
            # logger.debug(f"res_json={res_json}")
            if "推荐实例" in res_json:
                for i in res_json["推荐实例"]:
                    #  list_catalog 是资源名称, 从res_json中拆出来的
                    list_catalog.append(i[table_name])
                    # logger.debug(f"list_catalog={list_catalog}")
            if "分析步骤" in res_json:
                list_catalog_reason = res_json["分析步骤"]
                # logger.debug(f"list_catalog_reason={list_catalog_reason}")
            if "相关信息" in res_json:
                if isinstance(res_json["相关信息"], str):
                    list_catalog_reason = list_catalog_reason + '<br>' + res_json["相关信息"]
                # 如果“相关信息”的值是列表，这里使用空格作为分隔符连接列表元素
                elif isinstance(res_json["相关信息"], list):
                    list_catalog_reason = list_catalog_reason + '<br>' + ' '.join(res_json["相关信息"])
                else:
                    # 对于其他类型的数据，尝试直接转换成字符串
                    list_catalog_reason = list_catalog_reason + '<br>' + str(res_json["相关信息"])
                # logger.debug(f"list_catalog_reason={list_catalog_reason}")

        else:
            res_json = {}
        end1 = time.ctime()
        end = time.time()
        logger.info(f'开始时间 = {start1}, 结束时间 = {end1}, 调用大模型耗时 = {end - start}')

        # res_json 是大模型原始返回结果的json部分, 要求大模型返回json形式
        # list_catalog 是资源名称, 从res_json中拆出来的
        # list_catalog_reason是分析思路话术, 从res_json中拆出来的
        logger.info(
            f'大模型返回结果整理后: \nlist_catalog = {list_catalog}\nlist_catalog_reason = {list_catalog_reason}\nres_json = {res_json}')

        return list_catalog, list_catalog_reason, res_json
    else:
        return [], '', {}



# 数据应用思路话术中打上搜索结果资源编号的标签
# origin(reason) 是话术, cites是"推荐实例"

# def add_label(origin, cites: list, a: int):
def add_label(reason, cites: list, a: int):
    """
    Add labels to a given string based on the provided list of citations.

    The function searches for occurrences of citation identifiers, full citations, or citation names within the reason string.
    For each found occurrence, it appends a formatted label and updates the reason string. The function also removes processed
    citations from the cites list. If no citation is found, the function returns the original string and '0' as an indicator.
    Otherwise, it returns the modified string and '1'.

    :raises:
        - No specific exceptions are raised by this function.
    :returns:
        - A tuple containing the updated reason string and a status indicator ('1' if any citation was processed, '0' otherwise).
    :param reason: The original string to be updated with labels.
    :type reason: str
    :param cites: A list of citations, where each citation is a string in the format "id|name".
    :type cites: list
    :param a: An integer used to start the numbering of the labels.
    :type a: int
    """
    # reason 是话术, cite是"推荐实例"
    # 2025.12.03：cites中有些资源reason中没提到， 这改成允许的；但是reason中有的，cites中必须有；
    # 因为add_label会在reason中添加标签， 要求一一对应，以上不好实现，暂缓处理
    num = a
    logger.info(f"reason={reason}")
    logger.info(f"cites={cites}")
    for cite in cites[:]:
        # title = cite
        logger.info(f'cite={cite}')
        cite_id = cite.split('|')[0]
        cite_name = cite.split('|')[1]
        logger.info(f'cite_id={cite_id}, cite_name={cite_name}')
        # 先在话术中搜索完整的cite名称
        index = reason.find("'" + cite + "'")
        logger.info(f'index={index}')
        # reason.find 返回 -1 代表检索失败
        #  reason= res_view_reason =

        if index != -1:
            local = index + len(cite) + 2
            target = "<i slice_idx=0>{}</i>".format(num + 1)
            reason = reason[:local] + target + reason[local:]
            # 这里有bug, 比如一个cite为'8|房屋基本信息', 那么会把'28|居民房关系'也替换掉
            # reason = reason.replace(cite_id + '|', '')
            reason = reason.replace("'"+ cite_id + "|", "'")
            cites.remove(cite)
            num += 1
        # 如果在话术中没有找到完整的cite名称, 先查找cite_id,再查找cite_name
        else:
            index = reason.find("'" + cite_id + "'")
            if index != -1:
                local = index + len(cite_id) + 2
                target = "<i slice_idx=0>{}</i>".format(num + 1)
                reason = reason[:local] + target + reason[local:]
                reason = reason.replace(cite_id, cite_name)
                cites.remove(cite)
                num += 1
            else:
                index = reason.find("'" + cite_name + "'")
                if index != -1:
                    local = index + len(cite_name) + 2
                    target = "<i slice_idx=0>{}</i>".format(num + 1)
                    reason = reason[:local] + target + reason[local:]
                    cites.remove(cite)
                    num += 1
                else:
                    return reason, '0'
            # return reason, '0'

    return reason, '1'


# 数据应用思路话术中打上搜索结果资源编号的标签
# 专用于指标
def add_label_easy(reason, cites):
    """
    Add labels to a given reason string based on a list of citations.

    Summary:
    This function processes a list of citation strings, extracting a specific
    part from each and appending it to the reason string with an index label.
    The index is formatted within an HTML-like tag. The final result is a
    concatenated string of all processed citations with their respective
    index labels, ending with a period.

    Args:
        reason (str): The initial string to which the processed citations will be appended.
        cites (list[str]): A list of citation strings, where each string is expected
                           to contain at least one '|' character for splitting.

    Returns:
        str: The modified reason string, now containing the processed citations
             and their index labels, concluded with a period.
    """
    for num, cite in enumerate(cites):
        target = "<i slice_idx=0>{}</i>".format(num + 1)
        reason += cite.split('|')[1] + target + ','
    reason = reason[:-1]
    reason += "."
    return reason


async def get_user_allowed_asset_type(search_params)->list:
    # 根据用户的角色判断可以搜索到的资源类型, 在全部tab的问答中,只有应用开发者 application-developer 可以搜到接口服务
    # 待确认问题: 如果是在接口服务tab中,也要受这个限制吗?或者是在该tab, 就没有问答功能?
    # filter_conds = search_params.filter
    # asset_type = filter_conds.get('asset_type', '')
    asset_type = search_params.filter.get('asset_type', '')
    # if asset_type==[-1]:assert_type_v=['1','2', '3',"4"]。在“全部“tab中，分析问答型搜索接口不出“指标”了
    # 只有 application-developer 可以搜到接口服务
    if asset_type == [-1]:  # 全部tab
        # 只有应用开发者的角色可以搜到接口服务
        # 实际上数据目录不会和逻辑视图tab,接口服务tab,指标tab同时出现, 所以以下的1没有必要,待确认后修改
        if "application-developer" in search_params.roles:
            # 恢复分析问答型搜索返回指标
            # catalog = "1"  # 目录
            # api = "2"  # API
            # view = "3"  # 视图
            # metric = "4"  # 指标 ？
            allowed_asset_type = ['1', '2', '3', '4']
        else:
            allowed_asset_type = ['1', '3', '4']
    else:  # 如果不是全部tab,就按照入参明确的资源类型确定搜索结果的资源类型
        allowed_asset_type = asset_type
    # 这里的 subject_id 是用户id
    return allowed_asset_type

async def get_user_authed_resource(headers, find_number_api, search_params):
    # 获取用户拥有权限的所有资源id, auth_id
    try:
        auth_id = await find_number_api.user_all_auth(
            headers=headers,
            subject_id=search_params.subject_id
        )
    except Exception as e:
        logger.error(f"取用户拥有权限的所有资源id，发生错误：{e}")
        # return ANALYSIS_SEARCH_EMPTY_RESULT
        return []

    # 数据运营工程师,数据开发工程师在列表可以搜未上线的资源, 但是在问答区域也必须是已上线的资源
    if "data-operation-engineer" in search_params.roles or "data-development-engineer" in search_params.roles:
        logger.info('用户是数据开发工程师和运营工程师')
    else:
        logger.info(f'该用户有权限的id = {auth_id}')
    return auth_id


async def keep_authed_online_resource(headers, search_params, find_number_api, all_hits, allowed_asset_type, auth_id):
    # pro_data_formview(旧代码中pro_data） 是逻辑视图
    # pro_data_svc(旧代码中resour）是接口服务
    # indicator是指标
    pro_data_formview, pro_data_formview_id, pro_data_svc, pro_data_indicator = [], [], [], []
    for num, hit in enumerate(all_hits):
        # 描述和名称拼起来作为提示词的一部分
        description = hit['_source']['description'] if 'description' in hit['_source'].keys() else '暂无描述'
        # asset_type: 1数据目录 2接口服务 3逻辑视图 4指标
        # 从图谱get的i['_source']['asset_type']为字符型
        # 分析问答型搜索要求必须是已经上线的资源
        # 向量搜索变成了可以搜所有的点,不仅是中间的点,所以要把中间的点过滤出来
        valid_online_statuses = {'online', 'down-auditing', 'down-reject'}
        has_asset_type = 'asset_type' in hit['_source']
        asset_type_valid = has_asset_type and hit['_source']['asset_type'] in {str(t) for t in allowed_asset_type}

        online_status_valid = hit['_source'].get('online_status') in valid_online_statuses

        # if 'asset_type' in i['_source'].keys() and i['_source']['asset_type'] in [str(i) for i in assert_type_v] and \
        #         i['_source']['online_status'] in ['online', 'down-auditing', 'down-reject']:
        if has_asset_type and asset_type_valid and online_status_valid:
            res_auth = await find_number_api.sub_user_auth_state(
                assets=hit['_source'],
                params=search_params,
                headers=headers,
                auth_id=auth_id
            )
            # 为每一个召回资源增加一个id字段， ['_selfid']，用其在召回结果中的序号来标识
            hit['_selfid'] = str(num)
            logger.info(f"hit['_source']['resourcename'] = {hit['_source']['resourcename']}\nres_auth = {res_auth}")
            # 3 逻辑视图
            if hit['_source']['asset_type'] == '3' and res_auth == "allow":
                # 描述和名称拼起来作为提示词的一部分
                # pro_data是一个列表， 其中每个元素是一个字典， 字典的key是拼接成的一个字符串“<序号>|资源名称"， value是资源的描述
                # 大模型提示词中的 "table_name": "380ab8|t_chemical_product" ,"380ab8|t_chemical_product"就说字典key一样的字符串格式
                pro_data_formview.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
                pro_data_formview_id.append(hit["_source"]["resourceid"])
            #  2接口服务
            if hit['_source']['asset_type'] == '2' and res_auth == "allow":
                pro_data_svc.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
            #  4指标
            if hit['_source']['asset_type'] == '4' and res_auth == "allow":
                pro_data_indicator.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})

        else:
            pass
    # 保留用户有权限并且已上线的资源    #
    # logger.debug('pro_data_formview = ', pro_data_formview)
    # logger.debug('pro_data_svc = ', pro_data_svc)
    # logger.debug('pro_data_indicator = ', pro_data_indicator)
    # pro_data_formview(旧代码中pro_data） 是逻辑视图
    # pro_data_svc(旧代码中resour）是接口服务
    # indicator是指标
    # logger.debug(f'pro_data_formview_id = \n{pro_data_formview_id}')
    return pro_data_formview, pro_data_formview_id, pro_data_svc, pro_data_indicator

async def keep_online_resource_no_auth(all_hits, allowed_asset_type):
    # pro_data_formview(旧代码中pro_data） 是逻辑视图
    # pro_data_svc(旧代码中resour）是接口服务
    # indicator是指标
    pro_data_formview, pro_data_formview_id, pro_data_svc, pro_data_indicator = [], [], [], []
    for num, hit in enumerate(all_hits):
        # 描述和名称拼起来作为提示词的一部分
        description = hit['_source']['description'] if 'description' in hit['_source'].keys() else '暂无描述'
        # asset_type: 1数据目录 2接口服务 3逻辑视图 4指标
        # 从图谱get的i['_source']['asset_type']为字符型
        # 分析问答型搜索要求必须是已经上线的资源
        # 向量搜索变成了可以搜所有的点,不仅是中间的点,所以要把中间的点过滤出来
        valid_online_statuses = {'online', 'down-auditing', 'down-reject'}
        has_asset_type = 'asset_type' in hit['_source']
        asset_type_valid = has_asset_type and hit['_source']['asset_type'] in {str(t) for t in allowed_asset_type}

        online_status_valid = hit['_source'].get('online_status') in valid_online_statuses

        # if 'asset_type' in i['_source'].keys() and i['_source']['asset_type'] in [str(i) for i in assert_type_v] and \
        #         i['_source']['online_status'] in ['online', 'down-auditing', 'down-reject']:
        if has_asset_type and asset_type_valid and online_status_valid:
            # res_auth = await find_number_api.sub_user_auth_state(
            #     assets=hit['_source'],
            #     params=search_params,
            #     headers=headers,
            #     auth_id=auth_id
            # )
            # 为每一个召回资源增加一个id字段， ['_selfid']，用其在召回结果中的序号来标识
            hit['_selfid'] = str(num)
            # logger.debug(i['_source']['resourcename'], res_auth)
            # 3 逻辑视图
            if hit['_source']['asset_type'] == '3':
                # 描述和名称拼起来作为提示词的一部分
                # pro_data是一个列表， 其中每个元素是一个字典， 字典的key是拼接成的一个字符串“<序号>|资源名称"， value是资源的描述
                # 大模型提示词中的 "table_name": "380ab8|t_chemical_product" ,"380ab8|t_chemical_product"就说字典key一样的字符串格式
                pro_data_formview.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
                pro_data_formview_id.append(hit["_source"]["resourceid"])
            #  2接口服务
            if hit['_source']['asset_type'] == '2':
                pro_data_svc.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})
            #  4指标
            if hit['_source']['asset_type'] == '4':
                pro_data_indicator.append({hit['_selfid'] + '|' + hit['_source']['resourcename']: description})

        else:
            pass
    # 保留用户有权限并且已上线的资源    #
    # logger.debug('pro_data_formview = ', pro_data_formview)
    # logger.debug('pro_data_svc = ', pro_data_svc)
    # logger.debug('pro_data_indicator = ', pro_data_indicator)
    # pro_data_formview(旧代码中pro_data） 是逻辑视图
    # pro_data_svc(旧代码中resour）是接口服务
    # indicator是指标
    # logger.debug(f'pro_data_formview_id = \n{pro_data_formview_id}')
    return pro_data_formview, pro_data_formview_id, pro_data_svc, pro_data_indicator

async def skip_model(resource_type:str):
    logger.info(f'{resource_type}: 大模型入参为空，减少此次交互')
    return [], [], [], '', {}


async def main():
    prompt_id_table = "enhance_table_template"
    table_name = 'table_name'
    ad_appid = prompt_svc.get_appid()
    prompt, prompt_id = await prompt_svc.from_anydata(appid=ad_appid, name=prompt_id_table)

    logger.debug(f'prompt = \n{prompt}')
    logger.debug(f'prompt_id = \n{prompt_id}')
    # `{'data_dict': str(data), 'query': query, 'QAG': str(q_answer)}`
    data = {"table1": "description1", "table2": "description2"}
    query = "知识产权分析"
    q_answer = {"Q":"Question","A":"Answer"}
    processed_prompt = prompt.replace("{{query}}", query)
    processed_prompt = processed_prompt.replace("{{data_dict}}", str(data))
    processed_prompt = processed_prompt.replace("{{QAG}}", str(q_answer))

    logger.debug(f'processed_prompt =\n{processed_prompt}')

    token_count = await prompt_svc.tokens_count(input_text=processed_prompt,model_name=settings.LLM_NAME,appid=ad_appid)
    logger.debug(f'token_count = \n{token_count}')

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

