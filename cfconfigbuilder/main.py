from google.cloud import bigquery
from google.cloud import storage
import tempfile
import json
import os

class FlattenerDatasetConfigStorage(object):
    def __init__(self):
        self.bucket_name = os.environ["config_bucket_name"]
    def upload_config(self,config):
        storage_client = storage.Client()
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob(os.environ["config_filename"])

        filepath = os.path.join(tempfile.gettempdir(), "tmp.json")
        with open(filepath, "w") as f:
            f.write(json.dumps(config))
        blob.upload_from_filename(filepath)

class FlattenerDatasetConfig(object):
    def __init__(self):
        self.query = """
        EXECUTE IMMEDIATE (
 WITH schemas AS (
  SELECT
    schema_name,
    LAST_VALUE(schema_name) OVER (PARTITION BY catalog_name ORDER BY schema_name ASC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS last_schema
  FROM
    INFORMATION_SCHEMA.SCHEMATA 
   -- where regexp_contains(schema_name,r'^\d+$')
), static AS (
  SELECT
    "SELECT dataset_id FROM `%s.__TABLES__` where regexp_contains(table_id,r'^ga_sessions.*\\\\d{8}$') group by 1" AS sql,
    " union all " AS cmd_u,
    " order by 1 " AS cmd_f 
)
SELECT
  ARRAY_TO_STRING(ARRAY_AGG(sql_command_rows),"") AS generated_sql_statement
FROM (
  SELECT
    CASE WHEN schemas.schema_name != schemas.last_schema THEN CONCAT(FORMAT(static.sql,schema_name),static.cmd_u)
         ELSE CONCAT(FORMAT(static.sql,schema_name),static.cmd_f)
     END AS sql_command_rows
  FROM
    static
  CROSS JOIN
    schemas
  ORDER BY
    schema_name ASC
      ) -- end of sub select
);  --end of dynamic SQL statement
"""

    def get_ga_datasets(self):
        ret_val = {"datasets": []}
        client = bigquery.Client()
        query_job = client.query(self.query)
        query_results = query_job.result()  # Waits for job to complete.
        for row in query_results:
            ret_val["datasets"].append(row.dataset_id)
        return ret_val
def build_ga_flattener_config(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <http://flask.pocoo.org/docs/1.0/api/#flask.Request>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>.
    """
    print("build_ga_flattener_config cloud function - start")
    config = FlattenerDatasetConfig()
    store = FlattenerDatasetConfigStorage()
    json_config = config.get_ga_datasets()
    store.upload_config(config=json_config)
    print("build_ga_flattener_config: {}".format(json.dumps(json_config)))
    print("build_ga_flattener_config cloud function - end")
