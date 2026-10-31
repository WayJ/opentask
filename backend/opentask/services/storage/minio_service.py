"""
MinIO 对象存储服务
支持文件上传、删除和 URL 生成，与 LocalStorageService 接口兼容
"""
import uuid
import mimetypes
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Tuple
from fastapi import UploadFile, HTTPException

from minio import Minio
from minio.error import S3Error

from opentask.config import config


class MinIOStorageService:
    """MinIO 对象存储服务，与 LocalStorageService 接口兼容"""

    def __init__(self):
        """初始化 MinIO 客户端"""
        self.client = Minio(
            config.minio_endpoint,
            access_key=config.minio_access_key,
            secret_key=config.minio_secret_key,
            secure=config.minio_secure
        )
        self.bucket_name = config.minio_bucket
        # 确保桶存在
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"MinIO bucket initialization failed: {e.message}"
            )

    def _generate_unique_filename(self, original_filename: str) -> str:
        """生成唯一文件名"""
        # 保留文件扩展名
        ext = Path(original_filename).suffix
        # 生成唯一 ID
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{ext}"

    def _get_mime_type(self, filename: str) -> str:
        """获取文件的 MIME 类型"""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'

    async def save_upload_file(
        self,
        upload_file: UploadFile,
        subdir: str = ''
    ) -> Tuple[str, str, int]:
        """
        保存上传的文件到 MinIO

        Args:
            upload_file: FastAPI UploadFile 对象
            subdir: 子目录（对象键前缀）

        Returns:
            (object_name, filename, file_size) 元组
            - object_name: MinIO 对象键（相当于存储路径）
            - filename: 原始文件名
            - file_size: 文件大小（字节）
        """
        # 生成唯一文件名
        unique_filename = self._generate_unique_filename(upload_file.filename)

        # 构建对象键（MinIO 的路径概念）
        if subdir:
            # 移除开头的斜杠并标准化路径
            subdir = subdir.strip('/')
            object_name = f"{subdir}/{unique_filename}"
        else:
            object_name = unique_filename

        # 读取文件内容到内存
        file_content = await upload_file.read()
        file_size = len(file_content)

        # 获取 MIME 类型
        mime_type = upload_file.content_type or self._get_mime_type(upload_file.filename or unique_filename)

        try:
            # 上传到 MinIO
            self.client.put_object(
                self.bucket_name,
                object_name,
                data=BytesIO(file_content),
                length=file_size,
                content_type=mime_type
            )
        except S3Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"MinIO upload failed: {e.message}"
            )
        finally:
            await upload_file.close()

        return object_name, upload_file.filename or unique_filename, file_size

    def delete_file(self, object_name: str) -> bool:
        """
        删除文件

        Args:
            object_name: MinIO 对象键

        Returns:
            是否删除成功
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False

    def get_file_path(self, object_name: str) -> str:
        """
        获取文件的访问路径（MinIO 中返回对象键）

        Args:
            object_name: MinIO 对象键

        Returns:
            对象键（用于兼容性，实际访问应使用 presigned URL）
        """
        return object_name

    def file_exists(self, object_name: str) -> bool:
        """
        检查文件是否存在

        Args:
            object_name: MinIO 对象键

        Returns:
            文件是否存在
        """
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False

    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """
        生成预签名访问 URL

        Args:
            object_name: MinIO 对象键
            expires: URL 有效期（秒），默认 1 小时

        Returns:
            预签名 URL
        """
        try:
            from datetime import timedelta
            # MinIO Python SDK 7.x 使用 timedelta
            return self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=timedelta(seconds=expires)
            )
        except S3Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate presigned URL: {e.message}"
            )

    def get_file_stream(self, object_name: str) -> BinaryIO:
        """
        获取文件流（用于下载）

        Args:
            object_name: MinIO 对象键

        Returns:
            文件流对象
        """
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            return response
        except S3Error as e:
            raise HTTPException(
                status_code=404 if e.code == 'NoSuchKey' else 500,
                detail=f"Failed to get file: {e.message}"
            )
