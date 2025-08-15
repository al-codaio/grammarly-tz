CREATE TABLE tensorzero.BatchIdByInferenceId\n(\n    `inference_id` UUID,\n    `batch_id` UUID\n)\nENGINE = MergeTree\nORDER BY inference_id\nSETTINGS index_granularity = 8192;
