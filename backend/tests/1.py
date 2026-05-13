from pymilvus import MilvusClient

client = MilvusClient(
    uri="http://localhost:19530",
    token="root:Milvus"
)

a=client.list_databases()

b=client.describe_database(
    db_name="test11"
)

print(a)
print(b)