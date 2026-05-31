# data_pipelines/orchestration/medical_data_pipeline.py
"""
ETL Pipeline for Medical Data Processing
Supports: Pandas, Polars, DuckDB for data transformations
"""

import pandas as pd
import polars as pl
import duckdb
from datetime import datetime, timedelta
from typing import Dict, List, Any
import asyncio
from kafka import KafkaProducer, KafkaConsumer
import json
import logging

logger = logging.getLogger(__name__)

class MedicalDataPipeline:
    """Enterprise data pipeline for medical data processing"""
    
    def __init__(self):
        self.duckdb_conn = duckdb.connect(':memory:')
        self._setup_duckdb_extensions()
        
    def _setup_duckdb_extensions(self):
        """Setup DuckDB extensions for advanced analytics"""
        self.duckdb_conn.execute("INSTALL httpfs")
        self.duckdb_conn.execute("LOAD httpfs")
        self.duckdb_conn.execute("INSTALL parquet")
        self.duckdb_conn.execute("LOAD parquet")
    
    async def extract_from_source(self, source_type: str, config: Dict) -> pd.DataFrame:
        """Extract data from various sources"""
        if source_type == "s3":
            return await self._extract_from_s3(config)
        elif source_type == "kafka":
            return await self._extract_from_kafka(config)
        elif source_type == "database":
            return await self._extract_from_database(config)
        elif source_type == "api":
            return await self._extract_from_api(config)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
    
    async def _extract_from_s3(self, config: Dict) -> pd.DataFrame:
        """Extract data from AWS S3"""
        import boto3
        s3 = boto3.client('s3')
        
        bucket = config['bucket']
        key = config['key']
        
        # Use DuckDB to query S3 files directly
        query = f"SELECT * FROM read_parquet('s3://{bucket}/{key}')"
        result = self.duckdb_conn.execute(query).fetchdf()
        return result
    
    async def _extract_from_kafka(self, config: Dict) -> pd.DataFrame:
        """Extract data from Kafka streams"""
        consumer = KafkaConsumer(
            config['topic'],
            bootstrap_servers=config['bootstrap_servers'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        messages = []
        for msg in consumer:
            messages.append(msg.value)
            if len(messages) >= config.get('batch_size', 100):
                break
        
        return pd.DataFrame(messages)
    
    def transform_with_polars(self, df: pd.DataFrame, transformations: List[Dict]) -> pl.DataFrame:
        """Transform data using Polars for high performance"""
        pl_df = pl.from_pandas(df)
        
        for transform in transformations:
            if transform['type'] == 'filter':
                pl_df = pl_df.filter(eval(f"pl_df.{transform['condition']}"))
            elif transform['type'] == 'aggregate':
                pl_df = pl_df.group_by(transform['group_by']).agg(
                    [pl.col(col).mean().alias(f"{col}_mean") for col in transform['columns']]
                )
            elif transform['type'] == 'join':
                other_df = transform['other_df']
                pl_df = pl_df.join(other_df, on=transform['on'], how=transform['how'])
            elif transform['type'] == 'window':
                pl_df = pl_df.with_columns([
                    pl.col(col).rolling_mean(window_size=transform['window']).alias(f"{col}_rolling_mean")
                    for col in transform['columns']
                ])
        
        return pl_df
    
    def analyze_with_duckdb(self, data: pl.DataFrame, analysis_query: str) -> Any:
        """Perform advanced analytics using DuckDB"""
        # Register DataFrame as temporary table
        self.duckdb_conn.register('temp_data', data.to_pandas())
        
        # Execute analysis query
        result = self.duckdb_conn.execute(analysis_query).fetchdf()
        return result
    
    async def load_to_warehouse(self, data: pd.DataFrame, warehouse_config: Dict):
        """Load data to cloud data warehouse"""
        warehouse_type = warehouse_config['type']
        
        if warehouse_type == 'bigquery':
            await self._load_to_bigquery(data, warehouse_config)
        elif warehouse_type == 'snowflake':
            await self._load_to_snowflake(data, warehouse_config)
        elif warehouse_type == 'redshift':
            await self._load_to_redshift(data, warehouse_config)
        elif warehouse_type == 'databricks':
            await self._load_to_databricks(data, warehouse_config)
    
    async def _load_to_bigquery(self, data: pd.DataFrame, config: Dict):
        """Load data to Google BigQuery"""
        from google.cloud import bigquery
        
        client = bigquery.Client()
        table_id = f"{config['project']}.{config['dataset']}.{config['table']}"
        
        job = client.load_table_from_dataframe(data, table_id)
        job.result()  # Wait for job to complete
        
        logger.info(f"Loaded {len(data)} rows to BigQuery")
    
    async def _load_to_snowflake(self, data: pd.DataFrame, config: Dict):
        """Load data to Snowflake"""
        import snowflake.connector
        
        conn = snowflake.connector.connect(
            account=config['account'],
            user=config['user'],
            password=config['password'],
            warehouse=config['warehouse'],
            database=config['database'],
            schema=config['schema']
        )
        
        cursor = conn.cursor()
        
        # Write data to staging table
        staging_table = f"{config['schema']}.{config['table']}_staging"
        cursor.execute(f"CREATE OR REPLACE TABLE {staging_table} AS SELECT * FROM {config['table']} LIMIT 0")
        
        # Use COPY command or write in batches
        for chunk in np.array_split(data, len(data)//1000 + 1):
            cursor.executemany(
                f"INSERT INTO {staging_table} VALUES ({','.join(['%s']*len(data.columns))})",
                chunk.values.tolist()
            )
        
        cursor.close()
        conn.close()
    
    def create_dbt_model(self, model_name: str, sql_query: str):
        """Create dbt model for transformations"""
        model_yaml = f"""
version: 2

models:
  - name: {model_name}
    description: "Medical data transformation model"
    columns:
      - name: id
        description: "Primary key"
        tests:
          - unique
          - not_null
      - name: created_at
        description: "Record creation timestamp"
    config:
      materialized: table
      partition_by:
        field: created_at
        data_type: date
        granularity: day
      cluster_by: ["user_id"]
        """
        
        with open(f"data_pipelines/transformations/{model_name}.sql", 'w') as f:
            f.write(sql_query)
        
        with open(f"data_pipelines/transformations/{model_name}.yml", 'w') as f:
            f.write(model_yaml)
    
    def run_airflow_dag(self, dag_config: Dict):
        """Generate Airflow DAG configuration"""
        dag_code = f'''
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

default_args = {{
    'owner': 'healthbot',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5)
}}

dag = DAG(
    '{dag_config['dag_id']}',
    default_args=default_args,
    description='{dag_config['description']}',
    schedule_interval='{dag_config['schedule']}',
    catchup=False,
    tags=['medical', 'etl']
)

def extract_task(**context):
    """Extract data from source"""
    from data_pipelines.orchestration.medical_data_pipeline import MedicalDataPipeline
    pipeline = MedicalDataPipeline()
    data = await pipeline.extract_from_source('{dag_config['source_type']}', {dag_config['source_config']})
    return data

def transform_task(**context):
    """Transform data"""
    ti = context['ti']
    data = ti.xcom_pull(task_ids='extract')
    pipeline = MedicalDataPipeline()
    transformed = pipeline.transform_with_polars(data, {dag_config['transformations']})
    return transformed

def load_task(**context):
    """Load to warehouse"""
    ti = context['ti']
    data = ti.xcom_pull(task_ids='transform')
    pipeline = MedicalDataPipeline()
    await pipeline.load_to_warehouse(data, {dag_config['warehouse_config']})

extract = PythonOperator(
    task_id='extract',
    python_callable=extract_task,
    provide_context=True,
    dag=dag
)

transform = PythonOperator(
    task_id='transform',
    python_callable=transform_task,
    provide_context=True,
    dag=dag
)

load = PythonOperator(
    task_id='load',
    python_callable=load_task,
    provide_context=True,
    dag=dag
)

extract >> transform >> load
'''
        
        with open(f"data_pipelines/orchestration/dags/{dag_config['dag_id']}.py", 'w') as f:
            f.write(dag_code)
        
        return dag_code

# Initialize pipeline
data_pipeline = MedicalDataPipeline()
