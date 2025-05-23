from Initialize import CInitialize
import pinecone

from logConfig import get_logger

logger = get_logger("helper.vectorDB")


def DeleteNamespace(index_name, namespace):
    """
    Delete a namespace from a Pinecone index.

    Parameters:
    index_name (str): The name of the Pinecone index to delete the namespace from.
    namespace (str): The name of the namespace to delete.

    Returns:
    None
    """
    logger.info(f"Attempting to delete namespace '{namespace}' from index '{index_name}'")
    try:
        objPinecone = CInitialize.MInitializePinecone(index_name)
        index = objPinecone.Index(index_name)
        index.delete(delete_all=True, namespace=namespace)
        logger.info(f"Namespace '{namespace}' deleted from Pinecone index '{index_name}'.")
    except AttributeError as e:
        logger.error(f"AttributeError: {e}")
        print(f"Error: {e}")
    except Exception as e:
        # Handle NotFoundException and any other exceptions
        if hasattr(pinecone, 'core') and hasattr(pinecone.core, 'client') and hasattr(pinecone.core.client, 'exceptions'):
            NotFoundException = getattr(pinecone.core.client.exceptions, 'NotFoundException', None)
            if NotFoundException and isinstance(e, NotFoundException):
                logger.warning(f"Namespace '{namespace}' not found in Pinecone index '{index_name}': {e}")
                print(f"Namespace not found: {e}")
                return
        logger.error(f"Unexpected error while deleting namespace '{namespace}': {e}")
        print(f"Unexpected error: {e}")