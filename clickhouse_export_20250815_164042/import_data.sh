#!/bin/bash
# Import ClickHouse data exported by export_clickhouse_data.py

set -e

# Configuration
CLICKHOUSE_HOST="${CLICKHOUSE_HOST:-localhost}"
CLICKHOUSE_PORT="${CLICKHOUSE_PORT:-8123}"
CLICKHOUSE_USER="${CLICKHOUSE_USER:-chuser}"
CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:-chpassword}"
CLICKHOUSE_DATABASE="${CLICKHOUSE_DATABASE:-tensorzero}"

echo "Importing ClickHouse data to $CLICKHOUSE_HOST:$CLICKHOUSE_PORT"
echo "Database: $CLICKHOUSE_DATABASE"
echo ""

# Function to execute ClickHouse query
execute_query() {
    clickhouse-client \
        --host "$CLICKHOUSE_HOST" \
        --port "$CLICKHOUSE_PORT" \
        --user "$CLICKHOUSE_USER" \
        --password "$CLICKHOUSE_PASSWORD" \
        --database "$CLICKHOUSE_DATABASE" \
        --query "$1"
}

# Function to import CSV file
import_csv() {
    local table=$1
    local file=$2
    
    if [ -f "$file" ]; then
        echo "Importing $table from $file..."
        clickhouse-client \
            --host "$CLICKHOUSE_HOST" \
            --port "$CLICKHOUSE_PORT" \
            --user "$CLICKHOUSE_USER" \
            --password "$CLICKHOUSE_PASSWORD" \
            --database "$CLICKHOUSE_DATABASE" \
            --query "INSERT INTO $table FORMAT CSVWithNames" < "$file"
        echo "✓ Imported $table"
    fi
}

# Create database if it doesn't exist
echo "Creating database if not exists..."
clickhouse-client \
    --host "$CLICKHOUSE_HOST" \
    --port "$CLICKHOUSE_PORT" \
    --user "$CLICKHOUSE_USER" \
    --password "$CLICKHOUSE_PASSWORD" \
    --query "CREATE DATABASE IF NOT EXISTS $CLICKHOUSE_DATABASE"

# Import schemas
echo ""
echo "Creating tables..."

if [ -f "BatchIdByInferenceId_schema.sql" ]; then
    echo "Creating table BatchIdByInferenceId..."
    execute_query "$(cat BatchIdByInferenceId_schema.sql)"
fi

if [ -f "BatchIdByInferenceIdView_schema.sql" ]; then
    echo "Creating table BatchIdByInferenceIdView..."
    execute_query "$(cat BatchIdByInferenceIdView_schema.sql)"
fi

if [ -f "BatchModelInference_schema.sql" ]; then
    echo "Creating table BatchModelInference..."
    execute_query "$(cat BatchModelInference_schema.sql)"
fi

if [ -f "BatchRequest_schema.sql" ]; then
    echo "Creating table BatchRequest..."
    execute_query "$(cat BatchRequest_schema.sql)"
fi

if [ -f "BooleanMetricFeedback_schema.sql" ]; then
    echo "Creating table BooleanMetricFeedback..."
    execute_query "$(cat BooleanMetricFeedback_schema.sql)"
fi

if [ -f "BooleanMetricFeedbackByTargetId_schema.sql" ]; then
    echo "Creating table BooleanMetricFeedbackByTargetId..."
    execute_query "$(cat BooleanMetricFeedbackByTargetId_schema.sql)"
fi

if [ -f "BooleanMetricFeedbackByTargetIdView_schema.sql" ]; then
    echo "Creating table BooleanMetricFeedbackByTargetIdView..."
    execute_query "$(cat BooleanMetricFeedbackByTargetIdView_schema.sql)"
fi

if [ -f "BooleanMetricFeedbackTagView_schema.sql" ]; then
    echo "Creating table BooleanMetricFeedbackTagView..."
    execute_query "$(cat BooleanMetricFeedbackTagView_schema.sql)"
fi

if [ -f "ChatInference_schema.sql" ]; then
    echo "Creating table ChatInference..."
    execute_query "$(cat ChatInference_schema.sql)"
fi

if [ -f "ChatInferenceByEpisodeIdView_schema.sql" ]; then
    echo "Creating table ChatInferenceByEpisodeIdView..."
    execute_query "$(cat ChatInferenceByEpisodeIdView_schema.sql)"
fi

if [ -f "ChatInferenceByIdView_schema.sql" ]; then
    echo "Creating table ChatInferenceByIdView..."
    execute_query "$(cat ChatInferenceByIdView_schema.sql)"
fi

if [ -f "ChatInferenceDatapoint_schema.sql" ]; then
    echo "Creating table ChatInferenceDatapoint..."
    execute_query "$(cat ChatInferenceDatapoint_schema.sql)"
fi

if [ -f "ChatInferenceTagView_schema.sql" ]; then
    echo "Creating table ChatInferenceTagView..."
    execute_query "$(cat ChatInferenceTagView_schema.sql)"
fi

if [ -f "CommentFeedback_schema.sql" ]; then
    echo "Creating table CommentFeedback..."
    execute_query "$(cat CommentFeedback_schema.sql)"
fi

if [ -f "CommentFeedbackByTargetId_schema.sql" ]; then
    echo "Creating table CommentFeedbackByTargetId..."
    execute_query "$(cat CommentFeedbackByTargetId_schema.sql)"
fi

if [ -f "CommentFeedbackByTargetIdView_schema.sql" ]; then
    echo "Creating table CommentFeedbackByTargetIdView..."
    execute_query "$(cat CommentFeedbackByTargetIdView_schema.sql)"
fi

if [ -f "CommentFeedbackTagView_schema.sql" ]; then
    echo "Creating table CommentFeedbackTagView..."
    execute_query "$(cat CommentFeedbackTagView_schema.sql)"
fi

if [ -f "DemonstrationFeedback_schema.sql" ]; then
    echo "Creating table DemonstrationFeedback..."
    execute_query "$(cat DemonstrationFeedback_schema.sql)"
fi

if [ -f "DemonstrationFeedbackByInferenceId_schema.sql" ]; then
    echo "Creating table DemonstrationFeedbackByInferenceId..."
    execute_query "$(cat DemonstrationFeedbackByInferenceId_schema.sql)"
fi

if [ -f "DemonstrationFeedbackByInferenceIdView_schema.sql" ]; then
    echo "Creating table DemonstrationFeedbackByInferenceIdView..."
    execute_query "$(cat DemonstrationFeedbackByInferenceIdView_schema.sql)"
fi

if [ -f "DemonstrationFeedbackTagView_schema.sql" ]; then
    echo "Creating table DemonstrationFeedbackTagView..."
    execute_query "$(cat DemonstrationFeedbackTagView_schema.sql)"
fi

if [ -f "DeploymentID_schema.sql" ]; then
    echo "Creating table DeploymentID..."
    execute_query "$(cat DeploymentID_schema.sql)"
fi

if [ -f "DynamicEvaluationRun_schema.sql" ]; then
    echo "Creating table DynamicEvaluationRun..."
    execute_query "$(cat DynamicEvaluationRun_schema.sql)"
fi

if [ -f "DynamicEvaluationRunByProjectName_schema.sql" ]; then
    echo "Creating table DynamicEvaluationRunByProjectName..."
    execute_query "$(cat DynamicEvaluationRunByProjectName_schema.sql)"
fi

if [ -f "DynamicEvaluationRunByProjectNameView_schema.sql" ]; then
    echo "Creating table DynamicEvaluationRunByProjectNameView..."
    execute_query "$(cat DynamicEvaluationRunByProjectNameView_schema.sql)"
fi

if [ -f "DynamicEvaluationRunEpisode_schema.sql" ]; then
    echo "Creating table DynamicEvaluationRunEpisode..."
    execute_query "$(cat DynamicEvaluationRunEpisode_schema.sql)"
fi

if [ -f "DynamicEvaluationRunEpisodeByRunId_schema.sql" ]; then
    echo "Creating table DynamicEvaluationRunEpisodeByRunId..."
    execute_query "$(cat DynamicEvaluationRunEpisodeByRunId_schema.sql)"
fi

if [ -f "DynamicEvaluationRunEpisodeByRunIdView_schema.sql" ]; then
    echo "Creating table DynamicEvaluationRunEpisodeByRunIdView..."
    execute_query "$(cat DynamicEvaluationRunEpisodeByRunIdView_schema.sql)"
fi

if [ -f "DynamicInContextLearningExample_schema.sql" ]; then
    echo "Creating table DynamicInContextLearningExample..."
    execute_query "$(cat DynamicInContextLearningExample_schema.sql)"
fi

if [ -f "FeedbackTag_schema.sql" ]; then
    echo "Creating table FeedbackTag..."
    execute_query "$(cat FeedbackTag_schema.sql)"
fi

if [ -f "FloatMetricFeedback_schema.sql" ]; then
    echo "Creating table FloatMetricFeedback..."
    execute_query "$(cat FloatMetricFeedback_schema.sql)"
fi

if [ -f "FloatMetricFeedbackByTargetId_schema.sql" ]; then
    echo "Creating table FloatMetricFeedbackByTargetId..."
    execute_query "$(cat FloatMetricFeedbackByTargetId_schema.sql)"
fi

if [ -f "FloatMetricFeedbackByTargetIdView_schema.sql" ]; then
    echo "Creating table FloatMetricFeedbackByTargetIdView..."
    execute_query "$(cat FloatMetricFeedbackByTargetIdView_schema.sql)"
fi

if [ -f "FloatMetricFeedbackTagView_schema.sql" ]; then
    echo "Creating table FloatMetricFeedbackTagView..."
    execute_query "$(cat FloatMetricFeedbackTagView_schema.sql)"
fi

if [ -f "InferenceByEpisodeId_schema.sql" ]; then
    echo "Creating table InferenceByEpisodeId..."
    execute_query "$(cat InferenceByEpisodeId_schema.sql)"
fi

if [ -f "InferenceById_schema.sql" ]; then
    echo "Creating table InferenceById..."
    execute_query "$(cat InferenceById_schema.sql)"
fi

if [ -f "InferenceTag_schema.sql" ]; then
    echo "Creating table InferenceTag..."
    execute_query "$(cat InferenceTag_schema.sql)"
fi

if [ -f "JsonInference_schema.sql" ]; then
    echo "Creating table JsonInference..."
    execute_query "$(cat JsonInference_schema.sql)"
fi

if [ -f "JsonInferenceByEpisodeIdView_schema.sql" ]; then
    echo "Creating table JsonInferenceByEpisodeIdView..."
    execute_query "$(cat JsonInferenceByEpisodeIdView_schema.sql)"
fi

if [ -f "JsonInferenceByIdView_schema.sql" ]; then
    echo "Creating table JsonInferenceByIdView..."
    execute_query "$(cat JsonInferenceByIdView_schema.sql)"
fi

if [ -f "JsonInferenceDatapoint_schema.sql" ]; then
    echo "Creating table JsonInferenceDatapoint..."
    execute_query "$(cat JsonInferenceDatapoint_schema.sql)"
fi

if [ -f "JsonInferenceTagView_schema.sql" ]; then
    echo "Creating table JsonInferenceTagView..."
    execute_query "$(cat JsonInferenceTagView_schema.sql)"
fi

if [ -f "ModelInference_schema.sql" ]; then
    echo "Creating table ModelInference..."
    execute_query "$(cat ModelInference_schema.sql)"
fi

if [ -f "ModelInferenceCache_schema.sql" ]; then
    echo "Creating table ModelInferenceCache..."
    execute_query "$(cat ModelInferenceCache_schema.sql)"
fi

if [ -f "StaticEvaluationBooleanHumanFeedbackView_schema.sql" ]; then
    echo "Creating table StaticEvaluationBooleanHumanFeedbackView..."
    execute_query "$(cat StaticEvaluationBooleanHumanFeedbackView_schema.sql)"
fi

if [ -f "StaticEvaluationFloatHumanFeedbackView_schema.sql" ]; then
    echo "Creating table StaticEvaluationFloatHumanFeedbackView..."
    execute_query "$(cat StaticEvaluationFloatHumanFeedbackView_schema.sql)"
fi

if [ -f "StaticEvaluationHumanFeedback_schema.sql" ]; then
    echo "Creating table StaticEvaluationHumanFeedback..."
    execute_query "$(cat StaticEvaluationHumanFeedback_schema.sql)"
fi

if [ -f "TagChatInferenceView_schema.sql" ]; then
    echo "Creating table TagChatInferenceView..."
    execute_query "$(cat TagChatInferenceView_schema.sql)"
fi

if [ -f "TagInference_schema.sql" ]; then
    echo "Creating table TagInference..."
    execute_query "$(cat TagInference_schema.sql)"
fi

if [ -f "TagJsonInferenceView_schema.sql" ]; then
    echo "Creating table TagJsonInferenceView..."
    execute_query "$(cat TagJsonInferenceView_schema.sql)"
fi

if [ -f "TensorZeroMigration_schema.sql" ]; then
    echo "Creating table TensorZeroMigration..."
    execute_query "$(cat TensorZeroMigration_schema.sql)"
fi

# Import data
echo ""
echo "Importing data..."
import_csv "BatchIdByInferenceId" "BatchIdByInferenceId_data.csv"
import_csv "BatchIdByInferenceIdView" "BatchIdByInferenceIdView_data.csv"
import_csv "BatchModelInference" "BatchModelInference_data.csv"
import_csv "BatchRequest" "BatchRequest_data.csv"
import_csv "BooleanMetricFeedback" "BooleanMetricFeedback_data.csv"
import_csv "BooleanMetricFeedbackByTargetId" "BooleanMetricFeedbackByTargetId_data.csv"
import_csv "BooleanMetricFeedbackByTargetIdView" "BooleanMetricFeedbackByTargetIdView_data.csv"
import_csv "BooleanMetricFeedbackTagView" "BooleanMetricFeedbackTagView_data.csv"
import_csv "ChatInference" "ChatInference_data.csv"
import_csv "ChatInferenceByEpisodeIdView" "ChatInferenceByEpisodeIdView_data.csv"
import_csv "ChatInferenceByIdView" "ChatInferenceByIdView_data.csv"
import_csv "ChatInferenceDatapoint" "ChatInferenceDatapoint_data.csv"
import_csv "ChatInferenceTagView" "ChatInferenceTagView_data.csv"
import_csv "CommentFeedback" "CommentFeedback_data.csv"
import_csv "CommentFeedbackByTargetId" "CommentFeedbackByTargetId_data.csv"
import_csv "CommentFeedbackByTargetIdView" "CommentFeedbackByTargetIdView_data.csv"
import_csv "CommentFeedbackTagView" "CommentFeedbackTagView_data.csv"
import_csv "DemonstrationFeedback" "DemonstrationFeedback_data.csv"
import_csv "DemonstrationFeedbackByInferenceId" "DemonstrationFeedbackByInferenceId_data.csv"
import_csv "DemonstrationFeedbackByInferenceIdView" "DemonstrationFeedbackByInferenceIdView_data.csv"
import_csv "DemonstrationFeedbackTagView" "DemonstrationFeedbackTagView_data.csv"
import_csv "DeploymentID" "DeploymentID_data.csv"
import_csv "DynamicEvaluationRun" "DynamicEvaluationRun_data.csv"
import_csv "DynamicEvaluationRunByProjectName" "DynamicEvaluationRunByProjectName_data.csv"
import_csv "DynamicEvaluationRunByProjectNameView" "DynamicEvaluationRunByProjectNameView_data.csv"
import_csv "DynamicEvaluationRunEpisode" "DynamicEvaluationRunEpisode_data.csv"
import_csv "DynamicEvaluationRunEpisodeByRunId" "DynamicEvaluationRunEpisodeByRunId_data.csv"
import_csv "DynamicEvaluationRunEpisodeByRunIdView" "DynamicEvaluationRunEpisodeByRunIdView_data.csv"
import_csv "DynamicInContextLearningExample" "DynamicInContextLearningExample_data.csv"
import_csv "FeedbackTag" "FeedbackTag_data.csv"
import_csv "FloatMetricFeedback" "FloatMetricFeedback_data.csv"
import_csv "FloatMetricFeedbackByTargetId" "FloatMetricFeedbackByTargetId_data.csv"
import_csv "FloatMetricFeedbackByTargetIdView" "FloatMetricFeedbackByTargetIdView_data.csv"
import_csv "FloatMetricFeedbackTagView" "FloatMetricFeedbackTagView_data.csv"
import_csv "InferenceByEpisodeId" "InferenceByEpisodeId_data.csv"
import_csv "InferenceById" "InferenceById_data.csv"
import_csv "InferenceTag" "InferenceTag_data.csv"
import_csv "JsonInference" "JsonInference_data.csv"
import_csv "JsonInferenceByEpisodeIdView" "JsonInferenceByEpisodeIdView_data.csv"
import_csv "JsonInferenceByIdView" "JsonInferenceByIdView_data.csv"
import_csv "JsonInferenceDatapoint" "JsonInferenceDatapoint_data.csv"
import_csv "JsonInferenceTagView" "JsonInferenceTagView_data.csv"
import_csv "ModelInference" "ModelInference_data.csv"
import_csv "ModelInferenceCache" "ModelInferenceCache_data.csv"
import_csv "StaticEvaluationBooleanHumanFeedbackView" "StaticEvaluationBooleanHumanFeedbackView_data.csv"
import_csv "StaticEvaluationFloatHumanFeedbackView" "StaticEvaluationFloatHumanFeedbackView_data.csv"
import_csv "StaticEvaluationHumanFeedback" "StaticEvaluationHumanFeedback_data.csv"
import_csv "TagChatInferenceView" "TagChatInferenceView_data.csv"
import_csv "TagInference" "TagInference_data.csv"
import_csv "TagJsonInferenceView" "TagJsonInferenceView_data.csv"
import_csv "TensorZeroMigration" "TensorZeroMigration_data.csv"

echo ""
echo "Import completed!"
echo ""
echo "Verify with:"
echo "  clickhouse-client --query 'SHOW TABLES FROM $CLICKHOUSE_DATABASE'"
