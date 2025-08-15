# ClickHouse Export

This export was created on 2025-08-15 16:40:47

## Source Database
- Host: localhost
- Port: 8123
- Database: tensorzero
- Tables: 51

## Contents
- *_schema.sql: Table schemas (CREATE TABLE statements)
- *_data.csv: Table data in CSV format
- *_data.json: Table data in JSON format (for complex types)
- import_data.sh: Script to import data using native ClickHouse client
- import_data_docker.sh: Script to import data using Docker

## Import Instructions

### Using native ClickHouse client:
```bash
cd clickhouse_export_20250815_164042
./import_data.sh
```

### Using Docker:
```bash
cd clickhouse_export_20250815_164042
CONTAINER_NAME=your-clickhouse-container ./import_data_docker.sh
```

### Custom settings:
You can override the default settings using environment variables:
```bash
CLICKHOUSE_HOST=newhost CLICKHOUSE_PORT=9000 ./import_data.sh
```

## Tables Exported
- BatchIdByInferenceId
- BatchIdByInferenceIdView
- BatchModelInference
- BatchRequest
- BooleanMetricFeedback
- BooleanMetricFeedbackByTargetId
- BooleanMetricFeedbackByTargetIdView
- BooleanMetricFeedbackTagView
- ChatInference
- ChatInferenceByEpisodeIdView
- ChatInferenceByIdView
- ChatInferenceDatapoint
- ChatInferenceTagView
- CommentFeedback
- CommentFeedbackByTargetId
- CommentFeedbackByTargetIdView
- CommentFeedbackTagView
- DemonstrationFeedback
- DemonstrationFeedbackByInferenceId
- DemonstrationFeedbackByInferenceIdView
- DemonstrationFeedbackTagView
- DeploymentID
- DynamicEvaluationRun
- DynamicEvaluationRunByProjectName
- DynamicEvaluationRunByProjectNameView
- DynamicEvaluationRunEpisode
- DynamicEvaluationRunEpisodeByRunId
- DynamicEvaluationRunEpisodeByRunIdView
- DynamicInContextLearningExample
- FeedbackTag
- FloatMetricFeedback
- FloatMetricFeedbackByTargetId
- FloatMetricFeedbackByTargetIdView
- FloatMetricFeedbackTagView
- InferenceByEpisodeId
- InferenceById
- InferenceTag
- JsonInference
- JsonInferenceByEpisodeIdView
- JsonInferenceByIdView
- JsonInferenceDatapoint
- JsonInferenceTagView
- ModelInference
- ModelInferenceCache
- StaticEvaluationBooleanHumanFeedbackView
- StaticEvaluationFloatHumanFeedbackView
- StaticEvaluationHumanFeedback
- TagChatInferenceView
- TagInference
- TagJsonInferenceView
- TensorZeroMigration
