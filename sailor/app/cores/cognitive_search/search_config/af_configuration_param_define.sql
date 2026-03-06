INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_search_if_history_qa_enhance', '0', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_search_if_history_qa_enhance' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_search_if_kecc', '0', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_search_if_kecc' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_search_if_auth_in_find_data_qa', '1', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_search_if_auth_in_find_data_qa' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_vec_min_score_analysis_search', '0.5', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_vec_min_score_analysis_search' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_vec_knn_k_analysis_search', '20', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_vec_knn_k_analysis_search' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_vec_size_analysis_search', '20', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_vec_size_analysis_search' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_vec_min_score_kecc', '0.5', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_vec_min_score_kecc' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_vec_knn_k_kecc', '10', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_vec_knn_k_kecc' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_vec_size_kecc', '10', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_vec_size_kecc' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'kg_id_kecc', '6839', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'kg_id_kecc' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_vec_min_score_history_qa', '0.7', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_vec_min_score_history_qa' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_vec_knn_k_history_qa', '10', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_vec_knn_k_history_qa' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_vec_size_history_qa', '10', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_vec_size_history_qa' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'kg_id_history_qa', '19467', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'kg_id_history_qa' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_token_tactics_history_qa', '1', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_token_tactics_history_qa' and `type`='9');


INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_search_qa_llm_temperature', '0', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_search_qa_llm_temperature' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_search_qa_llm_top_p', '1', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_search_qa_llm_top_p' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_search_qa_llm_presence_penalty', '0', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_search_qa_llm_presence_penalty' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_search_qa_llm_frequency_penalty', '0', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_search_qa_llm_frequency_penalty' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_search_qa_llm_max_tokens', '8000', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_search_qa_llm_max_tokens' and `type`='9');

INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_search_qa_llm_input_len', '4000', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_search_qa_llm_input_len' and `type`='9');

USE af_configuration;
INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'sailor_search_qa_cites_num_limit', '50', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'sailor_search_qa_cites_num_limit' and `type`='9');

USE af_configuration;
INSERT  INTO `configuration`(`key`,`value`,`type`)
SELECT 'kn_id_catalog', 'cognitive_search_data_catalog', '9'
FROM DUAL WHERE NOT EXISTS(SELECT `key` FROM `configuration` WHERE `key` = 'kn_id_catalog' and `type`='9');

