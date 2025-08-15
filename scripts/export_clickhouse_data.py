#!/usr/bin/env python3
"""Export ClickHouse database for TensorZero to portable format."""

import os
import json
import clickhouse_connect
from datetime import datetime
import subprocess
import tarfile
import shutil

# ClickHouse connection settings
CLICKHOUSE_HOST = 'localhost'
CLICKHOUSE_PORT = 8123
CLICKHOUSE_USER = 'chuser'
CLICKHOUSE_PASSWORD = 'chpassword'
CLICKHOUSE_DATABASE = 'tensorzero'

# Export directory
EXPORT_DIR = f'clickhouse_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

def get_clickhouse_client():
    """Create ClickHouse client connection."""
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DATABASE
    )

def export_table_schema(client, table_name, export_path):
    """Export table schema (CREATE TABLE statement)."""
    result = client.command(f"SHOW CREATE TABLE {table_name}")
    
    schema_file = os.path.join(export_path, f"{table_name}_schema.sql")
    with open(schema_file, 'w') as f:
        f.write(result + ";\n")
    
    print(f"  ✓ Exported schema for {table_name}")

def export_table_data(client, table_name, export_path):
    """Export table data to CSV format."""
    csv_file = os.path.join(export_path, f"{table_name}_data.csv")
    
    # Get row count first
    count_result = client.query(f"SELECT COUNT(*) FROM {table_name}")
    row_count = count_result.result_rows[0][0] if count_result.result_rows else 0
    
    if row_count == 0:
        print(f"  ⚠ Table {table_name} is empty, skipping data export")
        return
    
    # Export to CSV using ClickHouse native format
    query = f"SELECT * FROM {table_name} FORMAT CSVWithNames"
    
    try:
        # Use command-line client for better performance with large datasets
        cmd = [
            'docker', 'exec', 'grammarly-tz-clickhouse-1',
            'clickhouse-client',
            '--user', CLICKHOUSE_USER,
            '--password', CLICKHOUSE_PASSWORD,
            '--database', CLICKHOUSE_DATABASE,
            '--query', query
        ]
        
        with open(csv_file, 'w') as f:
            subprocess.run(cmd, stdout=f, check=True)
        
        print(f"  ✓ Exported {row_count:,} rows from {table_name}")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Error exporting {table_name}: {e}")

def export_table_data_json(client, table_name, export_path):
    """Export table data to JSON format for tables with complex types."""
    json_file = os.path.join(export_path, f"{table_name}_data.json")
    
    # Tables with complex types that need JSON export
    complex_tables = ['DynamicInContextLearningExample', 'JsonInference', 'ChatInference']
    
    if table_name not in complex_tables:
        return
    
    try:
        # Get all data
        result = client.query(f"SELECT * FROM {table_name}")
        
        # Convert to list of dicts
        columns = [col[0] for col in result.column_descriptions]
        data = []
        
        for row in result.result_rows:
            row_dict = {}
            for i, value in enumerate(row):
                # Handle special types
                if isinstance(value, bytes):
                    row_dict[columns[i]] = value.hex()
                elif isinstance(value, (list, dict)):
                    row_dict[columns[i]] = value
                else:
                    row_dict[columns[i]] = str(value) if value is not None else None
            data.append(row_dict)
        
        # Write to JSON
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"  ✓ Exported {len(data):,} rows from {table_name} to JSON")
    except Exception as e:
        print(f"  ⚠ Could not export {table_name} to JSON: {e}")

def create_import_script(export_path, tables):
    """Create a script to import the data on another machine."""
    import_script = """#!/bin/bash
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
    clickhouse-client \\
        --host "$CLICKHOUSE_HOST" \\
        --port "$CLICKHOUSE_PORT" \\
        --user "$CLICKHOUSE_USER" \\
        --password "$CLICKHOUSE_PASSWORD" \\
        --database "$CLICKHOUSE_DATABASE" \\
        --query "$1"
}

# Function to import CSV file
import_csv() {
    local table=$1
    local file=$2
    
    if [ -f "$file" ]; then
        echo "Importing $table from $file..."
        clickhouse-client \\
            --host "$CLICKHOUSE_HOST" \\
            --port "$CLICKHOUSE_PORT" \\
            --user "$CLICKHOUSE_USER" \\
            --password "$CLICKHOUSE_PASSWORD" \\
            --database "$CLICKHOUSE_DATABASE" \\
            --query "INSERT INTO $table FORMAT CSVWithNames" < "$file"
        echo "✓ Imported $table"
    fi
}

# Create database if it doesn't exist
echo "Creating database if not exists..."
clickhouse-client \\
    --host "$CLICKHOUSE_HOST" \\
    --port "$CLICKHOUSE_PORT" \\
    --user "$CLICKHOUSE_USER" \\
    --password "$CLICKHOUSE_PASSWORD" \\
    --query "CREATE DATABASE IF NOT EXISTS $CLICKHOUSE_DATABASE"

# Import schemas
echo ""
echo "Creating tables..."
"""

    # Add schema imports
    for table in tables:
        import_script += f"""
if [ -f "{table}_schema.sql" ]; then
    echo "Creating table {table}..."
    execute_query "$(cat {table}_schema.sql)"
fi
"""

    import_script += """
# Import data
echo ""
echo "Importing data..."
"""

    # Add data imports
    for table in tables:
        import_script += f'import_csv "{table}" "{table}_data.csv"\n'

    import_script += """
echo ""
echo "Import completed!"
echo ""
echo "Verify with:"
echo "  clickhouse-client --query 'SHOW TABLES FROM $CLICKHOUSE_DATABASE'"
"""

    script_file = os.path.join(export_path, 'import_data.sh')
    with open(script_file, 'w') as f:
        f.write(import_script)
    
    os.chmod(script_file, 0o755)
    print(f"  ✓ Created import script: {script_file}")

def create_docker_import_script(export_path, tables):
    """Create a script to import data using Docker."""
    docker_script = """#!/bin/bash
# Import ClickHouse data using Docker

set -e

# Configuration
CONTAINER_NAME="${CONTAINER_NAME:-clickhouse-server}"
CLICKHOUSE_USER="${CLICKHOUSE_USER:-chuser}"
CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:-chpassword}"
CLICKHOUSE_DATABASE="${CLICKHOUSE_DATABASE:-tensorzero}"

echo "Importing ClickHouse data to Docker container: $CONTAINER_NAME"
echo "Database: $CLICKHOUSE_DATABASE"
echo ""

# Function to execute ClickHouse query in Docker
execute_query() {
    docker exec "$CONTAINER_NAME" clickhouse-client \\
        --user "$CLICKHOUSE_USER" \\
        --password "$CLICKHOUSE_PASSWORD" \\
        --database "$CLICKHOUSE_DATABASE" \\
        --query "$1"
}

# Function to import CSV file via Docker
import_csv() {
    local table=$1
    local file=$2
    
    if [ -f "$file" ]; then
        echo "Importing $table from $file..."
        docker exec -i "$CONTAINER_NAME" clickhouse-client \\
            --user "$CLICKHOUSE_USER" \\
            --password "$CLICKHOUSE_PASSWORD" \\
            --database "$CLICKHOUSE_DATABASE" \\
            --query "INSERT INTO $table FORMAT CSVWithNames" < "$file"
        echo "✓ Imported $table"
    fi
}

# Create database if it doesn't exist
echo "Creating database if not exists..."
docker exec "$CONTAINER_NAME" clickhouse-client \\
    --user "$CLICKHOUSE_USER" \\
    --password "$CLICKHOUSE_PASSWORD" \\
    --query "CREATE DATABASE IF NOT EXISTS $CLICKHOUSE_DATABASE"

# Import schemas
echo ""
echo "Creating tables..."
"""

    # Add schema imports
    for table in tables:
        docker_script += f"""
if [ -f "{table}_schema.sql" ]; then
    echo "Creating table {table}..."
    execute_query "$(cat {table}_schema.sql)"
fi
"""

    docker_script += """
# Import data
echo ""
echo "Importing data..."
"""

    # Add data imports
    for table in tables:
        docker_script += f'import_csv "{table}" "{table}_data.csv"\n'

    docker_script += """
echo ""
echo "Import completed!"
echo ""
echo "Verify with:"
echo "  docker exec $CONTAINER_NAME clickhouse-client --query 'SHOW TABLES FROM $CLICKHOUSE_DATABASE'"
"""

    script_file = os.path.join(export_path, 'import_data_docker.sh')
    with open(script_file, 'w') as f:
        f.write(docker_script)
    
    os.chmod(script_file, 0o755)
    print(f"  ✓ Created Docker import script: {script_file}")

def main():
    """Main export function."""
    print(f"ClickHouse Data Export Tool")
    print(f"{'='*50}")
    print(f"Exporting from: {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/{CLICKHOUSE_DATABASE}")
    print(f"Export directory: {EXPORT_DIR}")
    print()
    
    # Create export directory
    os.makedirs(EXPORT_DIR, exist_ok=True)
    
    # Connect to ClickHouse
    print("Connecting to ClickHouse...")
    client = get_clickhouse_client()
    
    # Get all tables
    print("Fetching table list...")
    tables_result = client.query("SHOW TABLES")
    tables = [row[0] for row in tables_result.result_rows]
    
    print(f"Found {len(tables)} tables to export")
    print()
    
    # Export each table
    for table in sorted(tables):
        print(f"Exporting {table}...")
        
        # Export schema
        export_table_schema(client, table, EXPORT_DIR)
        
        # Export data
        export_table_data(client, table, EXPORT_DIR)
        
        # Export complex tables to JSON as well
        export_table_data_json(client, table, EXPORT_DIR)
        
        print()
    
    # Create import scripts
    print("Creating import scripts...")
    create_import_script(EXPORT_DIR, tables)
    create_docker_import_script(EXPORT_DIR, tables)
    
    # Create README
    readme_content = f"""# ClickHouse Export

This export was created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Source Database
- Host: {CLICKHOUSE_HOST}
- Port: {CLICKHOUSE_PORT}
- Database: {CLICKHOUSE_DATABASE}
- Tables: {len(tables)}

## Contents
- *_schema.sql: Table schemas (CREATE TABLE statements)
- *_data.csv: Table data in CSV format
- *_data.json: Table data in JSON format (for complex types)
- import_data.sh: Script to import data using native ClickHouse client
- import_data_docker.sh: Script to import data using Docker

## Import Instructions

### Using native ClickHouse client:
```bash
cd {EXPORT_DIR}
./import_data.sh
```

### Using Docker:
```bash
cd {EXPORT_DIR}
CONTAINER_NAME=your-clickhouse-container ./import_data_docker.sh
```

### Custom settings:
You can override the default settings using environment variables:
```bash
CLICKHOUSE_HOST=newhost CLICKHOUSE_PORT=9000 ./import_data.sh
```

## Tables Exported
{chr(10).join('- ' + table for table in sorted(tables))}
"""
    
    with open(os.path.join(EXPORT_DIR, 'README.md'), 'w') as f:
        f.write(readme_content)
    
    print(f"  ✓ Created README.md")
    
    # Create tarball
    print()
    print("Creating archive...")
    tar_filename = f"{EXPORT_DIR}.tar.gz"
    with tarfile.open(tar_filename, "w:gz") as tar:
        tar.add(EXPORT_DIR, arcname=os.path.basename(EXPORT_DIR))
    
    print(f"  ✓ Created archive: {tar_filename}")
    
    # Get archive size
    size_mb = os.path.getsize(tar_filename) / (1024 * 1024)
    print(f"  ✓ Archive size: {size_mb:.2f} MB")
    
    print()
    print(f"{'='*50}")
    print(f"Export completed successfully!")
    print(f"Archive: {tar_filename}")
    print(f"Directory: {EXPORT_DIR}/")
    print()
    print("To transfer to another machine:")
    print(f"  scp {tar_filename} user@remote-host:/path/to/destination/")
    print()
    print("To import on the destination machine:")
    print(f"  tar -xzf {tar_filename}")
    print(f"  cd {EXPORT_DIR}")
    print("  ./import_data.sh  # or ./import_data_docker.sh")

if __name__ == "__main__":
    main()