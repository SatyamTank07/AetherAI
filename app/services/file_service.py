# services/file_service.py
import boto3
import os
import uuid
from datetime import datetime
from typing import Tuple, Optional, List
from botocore.exceptions import ClientError
from scripts.helper.logConfig import get_logger
from scripts.config import load_config

logger = get_logger("FileService")

class FileService:
    def __init__(self):
        """Initialize Cloudflare R2 client using S3-compatible API"""
        try:
            config = load_config()
            
            # Cloudflare R2 credentials
            self.access_key_id = config.get("R2_ACCESS_KEY_ID")
            self.secret_access_key = config.get("R2_SECRET_ACCESS_KEY")
            self.account_id = config.get("R2_ACCOUNT_ID")
            self.bucket_name = config.get("R2_BUCKET_NAME")
            
            if not all([self.access_key_id, self.secret_access_key, self.account_id, self.bucket_name]):
                raise ValueError("Missing required R2 configuration parameters")
            
            # R2 endpoint URL
            self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
            
            # Initialize boto3 client for R2
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name='auto'  # R2 uses 'auto' as region
            )
            
            # Public domain for file URLs (if you have a custom domain configured)
            self.public_domain = config.get("R2_PUBLIC_DOMAIN")
            
            logger.info("FileService initialized successfully with Cloudflare R2")
            
        except Exception as e:
            logger.error(f"Error initializing FileService: {e}")
            raise

    async def upload_to_r2(self, file_content: bytes, filename: str, user_id: str) -> Tuple[str, str]:
        """
        Upload file to Cloudflare R2
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            user_id: User ID for organizing files
            
        Returns:
            Tuple of (file_url, file_key)
        """
        try:
            # Generate unique file key
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_key = f"users/{user_id}/documents/{datetime.utcnow().strftime('%Y/%m/%d')}/{unique_filename}"
            
            # Prepare metadata
            metadata = {
                'original-filename': filename,
                'user-id': user_id,
                'upload-timestamp': datetime.utcnow().isoformat(),
                'content-type': 'application/pdf'
            }
            
            # Upload to R2
            logger.info(f"Uploading file to R2: {file_key}")
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_content,
                ContentType='application/pdf',
                Metadata=metadata,
                # Add any additional parameters you need
                ServerSideEncryption='AES256',  # R2 supports this
                CacheControl='private, max-age=86400',  # 24 hours cache
            )
            
            # Generate file URL
            if self.public_domain:
                file_url = f"https://{self.public_domain}/{file_key}"
            else:
                file_url = f"{self.endpoint_url}/{self.bucket_name}/{file_key}"
            
            logger.info(f"File uploaded successfully to R2: {file_key}")
            return file_url, file_key
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"AWS Client Error uploading to R2: {error_code} - {e}")
            raise Exception(f"Failed to upload file to storage: {error_code}")
        except Exception as e:
            logger.error(f"Error uploading file to R2: {e}")
            raise Exception(f"Failed to upload file: {str(e)}")

    async def generate_download_url(self, file_key: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned download URL for a file
        
        Args:
            file_key: File key in R2
            expires_in: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned download URL
        """
        try:
            logger.info(f"Generating download URL for file: {file_key}")
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"Download URL generated successfully for: {file_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Error generating download URL: {e}")
            raise Exception(f"Failed to generate download URL: {str(e)}")

    async def delete_from_r2(self, file_key: str) -> bool:
        """
        Delete file from Cloudflare R2
        
        Args:
            file_key: File key in R2
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Deleting file from R2: {file_key}")
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            
            logger.info(f"File deleted successfully from R2: {file_key}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"File not found in R2: {file_key}")
                return True  # Consider it successful if file doesn't exist
            else:
                logger.error(f"Error deleting file from R2: {error_code} - {e}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file from R2: {e}")
            return False

    async def check_file_exists(self, file_key: str) -> bool:
        """
        Check if file exists in R2
        
        Args:
            file_key: File key in R2
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return False
            else:
                logger.error(f"Error checking file existence: {e}")
                raise Exception(f"Failed to check file existence: {str(e)}")

    async def get_file_metadata(self, file_key: str) -> Optional[dict]:
        """
        Get file metadata from R2
        
        Args:
            file_key: File key in R2
            
        Returns:
            File metadata dictionary or None if not found
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            
            return {
                'content_length': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {}),
                'etag': response.get('ETag')
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return None
            else:
                logger.error(f"Error getting file metadata: {e}")
                raise Exception(f"Failed to get file metadata: {str(e)}")

    async def list_user_files(self, user_id: str, max_keys: int = 1000) -> List[dict]:
        """
        List all files for a specific user
        
        Args:
            user_id: User ID
            max_keys: Maximum number of files to return
            
        Returns:
            List of file information dictionaries
        """
        try:
            prefix = f"users/{user_id}/documents/"
            files = []
            continuation_token = None
            
            logger.info(f"Listing files for user {user_id} with prefix {prefix}")
            
            while True:
                # Prepare parameters for listing objects
                params = {
                    'Bucket': self.bucket_name,
                    'Prefix': prefix,
                    'MaxKeys': max_keys
                }
                if continuation_token:
                    params['ContinuationToken'] = continuation_token
                
                # List objects in R2
                response = self.s3_client.list_objects_v2(**params)
                
                # Process contents if available
                if 'Contents' in response:
                    for obj in response['Contents']:
                        file_info = {
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat(),
                            'etag': obj['ETag'].strip('"')
                        }
                        
                        # Optionally retrieve metadata for more details
                        try:
                            metadata_response = self.s3_client.head_object(
                                Bucket=self.bucket_name,
                                Key=obj['Key']
                            )
                            file_info['metadata'] = metadata_response.get('Metadata', {})
                        except ClientError as e:
                            logger.warning(f"Could not fetch metadata for {obj['Key']}: {e}")
                            file_info['metadata'] = {}
                        
                        files.append(file_info)
                
                # Check for pagination
                if response.get('IsTruncated', False):
                    continuation_token = response.get('NextContinuationToken')
                else:
                    break
            
            logger.info(f"Found {len(files)} files for user {user_id}")
            return files
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Error listing files for user {user_id}: {error_code} - {e}")
            raise Exception(f"Failed to list files: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error listing files for user {user_id}: {e}")
            raise Exception(f"Failed to list files: {str(e)}")
