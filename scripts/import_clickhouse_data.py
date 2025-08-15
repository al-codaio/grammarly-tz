#!/usr/bin/env python3
"""Import ClickHouse data exported by export_clickhouse_data.py."""

import os
import json
import clickhouse_connect
import csv
import argparse
from datetime import datetime

def get_clickhouse_client(host, port, user, password, database):
    """Create ClickHouse client connection."""
    return clickhouse_connect.get_client(
        host=host,
        port=port,
        username=user,
        password=password,
        database=database
    )

def create_database_if_not_exists(client, database):
    """Create database if it doesn't exist."""
    try:
        client.command(f"CREATE DATABASE IF NOT EXISTS {database}")
        print(f"✓ Database '{database}' is ready")
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        raise

def import_schema(client, schema_file):
    """Import table schema from SQL file."""
    table_name = os.path.basename(schema_file).replace('_schema.sql', '')
    
    try:
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Drop table if exists (optional, uncomment if needed)
        # client.command(f"DROP TABLE IF EXISTS {table_name}")
        
        client.command(schema_sql)
        print(f"  ✓ Created table {table_name}")
        return True
    except Exception as e:
        print(f"  ✗ Error creating table {table_name}: {e}")
        return False

def import_csv_data(client, csv_file, table_name):
    """Import data from CSV file."""
    if not os.path.exists(csv_file):
        print(f"  ⚠ No data file found for {table_name}")
        return
    
    try:
        # Get file size
        file_size_mb = os.path.getsize(csv_file) / (1024 * 1024)
        
        # Count rows (excluding header)
        with open(csv_file, 'r') as f:
            row_count = sum(1 for line in f) - 1
        
        if row_count <= 0:
            print(f"  ⚠ No data in {table_name}")
            return
        
        print(f"  → Importing {row_count:,} rows ({file_size_mb:.2f} MB) into {table_name}...")
        
        # Read CSV and import in batches
        batch_size = 10000
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            
            batch = []
            imported = 0
            
            for row in reader:
                # Convert string representations back to proper types
                for key, value in row.items():
                    if value == '':
                        row[key] = None
                    elif value == 'True':
                        row[key] = True
                    elif value == 'False':
                        row[key] = False
                    elif value.startswith('[') and value.endswith(']'):
                        # Try to parse as list
                        try:
                            row[key] = json.loads(value)
                        except:
                            pass
                
                batch.append(row)
                
                if len(batch) >= batch_size:
                    client.insert(table_name, batch)
                    imported += len(batch)
                    print(f"    ... imported {imported:,} rows", end='\r')
                    batch = []
            
            # Import remaining batch
            if batch:
                client.insert(table_name, batch)
                imported += len(batch)
            
            print(f"  ✓ Imported {imported:,} rows into {table_name}      ")
            
    except Exception as e:
        print(f"  ✗ Error importing data for {table_name}: {e}")

def import_json_data(client, json_file, table_name):
    """Import data from JSON file (for complex types)."""
    if not os.path.exists(json_file):
        return
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        if not data:
            return
        
        print(f"  → Importing {len(data):,} rows from JSON into {table_name}...")
        
        # Import in batches
        batch_size = 1000
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            client.insert(table_name, batch)
            print(f"    ... imported {min(i+batch_size, len(data)):,} rows", end='\r')
        
        print(f"  ✓ Imported {len(data):,} rows from JSON into {table_name}      ")
        
    except Exception as e:
        print(f"  ⚠ Could not import JSON data for {table_name}: {e}")

def verify_import(client, table_name):
    """Verify imported data."""
    try:
        result = client.query(f"SELECT COUNT(*) FROM {table_name}")
        count = result.result_rows[0][0]
        print(f"  ✓ Verified: {table_name} has {count:,} rows")
    except Exception as e:
        print(f"  ✗ Could not verify {table_name}: {e}")

def main():
    """Main import function."""
    parser = argparse.ArgumentParser(description='Import ClickHouse data from export')
    parser.add_argument('export_dir', help='Directory containing exported data')
    parser.add_argument('--host', default='localhost', help='ClickHouse host')
    parser.add_argument('--port', type=int, default=8123, help='ClickHouse port')
    parser.add_argument('--user', default='chuser', help='ClickHouse user')
    parser.add_argument('--password', default='chpassword', help='ClickHouse password')
    parser.add_argument('--database', default='tensorzero', help='ClickHouse database')
    parser.add_argument('--verify-only', action='store_true', help='Only verify existing data')
    parser.add_argument('--use-json', action='store_true', help='Prefer JSON import for complex tables')
    
    args = parser.parse_args()
    
    print(f"ClickHouse Data Import Tool")
    print(f"{'='*50}")
    print(f"Importing to: {args.host}:{args.port}/{args.database}")
    print(f"From directory: {args.export_dir}")
    print()
    
    # Check export directory
    if not os.path.exists(args.export_dir):
        print(f"✗ Export directory not found: {args.export_dir}")
        return 1
    
    # Connect to ClickHouse
    print("Connecting to ClickHouse...")
    client = get_clickhouse_client(args.host, args.port, args.user, args.password, args.database)
    
    # Create database if needed
    if not args.verify_only:
        create_database_if_not_exists(client, args.database)
        print()
    
    # Get list of schema files
    schema_files = sorted([f for f in os.listdir(args.export_dir) if f.endswith('_schema.sql')])
    
    if args.verify_only:
        print("Verifying imported data...")
        for schema_file in schema_files:
            table_name = schema_file.replace('_schema.sql', '')
            verify_import(client, table_name)
    else:
        # Import schemas
        print("Creating tables...")
        for schema_file in schema_files:
            import_schema(client, os.path.join(args.export_dir, schema_file))
        
        print()
        print("Importing data...")
        
        # Import data
        for schema_file in schema_files:
            table_name = schema_file.replace('_schema.sql', '')
            csv_file = os.path.join(args.export_dir, f"{table_name}_data.csv")
            json_file = os.path.join(args.export_dir, f"{table_name}_data.json")
            
            # Check if we should use JSON import
            complex_tables = ['DynamicInContextLearningExample', 'JsonInference', 'ChatInference']
            if args.use_json and table_name in complex_tables and os.path.exists(json_file):
                import_json_data(client, json_file, table_name)
            else:
                import_csv_data(client, csv_file, table_name)
        
        print()
        print("Verifying import...")
        for schema_file in schema_files:
            table_name = schema_file.replace('_schema.sql', '')
            verify_import(client, table_name)
    
    print()
    print(f"{'='*50}")
    print("Import completed successfully!")
    
    # Show summary
    result = client.query(f"SELECT COUNT(*) FROM system.tables WHERE database = '{args.database}'")
    table_count = result.result_rows[0][0]
    print(f"Total tables in {args.database}: {table_count}")

if __name__ == "__main__":
    main()