import os
from azure.storage.blob import BlobServiceClient

AZURE_CONNECTION_STRING = os.getenv('AZURE_CONNECTION_STRING')
CONTAINER_NAME = os.getenv('AZURE_CONTAINER_NAME', 'nuamstoragemooresoto')

def get_blob_service_client():
    if not AZURE_CONNECTION_STRING:
        raise ValueError(
            "La variable de entorno 'AZURE_CONNECTION_STRING' no está configurada. "
            "Asegúrate de tenerla en tu archivo .env (local) o en el Dashboard de Render."
        )
    return BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

def get_container_client():
    service_client = get_blob_service_client()
    return service_client.get_container_client(CONTAINER_NAME)