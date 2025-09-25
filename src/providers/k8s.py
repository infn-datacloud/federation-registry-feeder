"""Kubernetes client object to retrieve data from openstack instance."""

import json
import logging
from typing import Any

import urllib3
from fed_mgr.v1.providers.schemas import ProviderType
from kubernetes.client.exceptions import ApiException
from pydantic import AnyHttpUrl

from kubernetes import client
from src.models.projects import Project
from src.models.quotas import BlockStorageQuota, ComputeQuota
from src.models.storageclass import StorageClass
from src.providers.core import ProviderClient


class KubernetesClient(ProviderClient):
    """Class to organize data retrieved from and Kubernetes instance."""

    def __init__(
        self,
        *,
        provider_name: str,
        provider_endpoint: AnyHttpUrl,
        project_id: str,
        idp_endpoint: AnyHttpUrl,
        idp_name: str,
        idp_audience: str,
        idp_token: str,
        user_group: str,
        timeout: int = 2,
        log_level: int = logging.INFO,
    ):
        """Create a kubernetes client to retrieve data."""
        super().__init__(
            provider_name=provider_name,
            provider_endpoint=str(provider_endpoint),
            provider_type=ProviderType.kubernetes,
            project_id=project_id,
            idp_endpoint=str(idp_endpoint),
            idp_name=idp_name,
            idp_token=idp_token,
            user_group=user_group,
            timeout=timeout,
            logger_name=f"{provider_name} - {project_id}",
            log_level=log_level,
        )
        self.ssl_ca_cert_path = None
        self.idp_audience = idp_audience

        # Connection is only defined, not yet opened
        self.client = self.create_connection()
        self.corev1 = client.CoreV1Api(self.client)
        self.storagev1 = client.StorageV1Api(self.client)

        self.project = None
        self.quotas = []
        self.storage_classes = []

    def create_connection(self) -> client.ApiClient:
        """Create a connection with the k8s cluster's V1 API."""
        msg = f"Creating connection using idp={self.idp_name}"
        self.logger.info(msg)
        conf = client.Configuration(
            host=self.provider_endpoint,
            api_key={"authorization": self.idp_token},
            api_key_prefix={"authorization": "Bearer"},
        )
        conf.ssl_ca_cert = self.ssl_ca_cert_path
        return client.ApiClient(conf)

    def retrieve_info(self):
        """Connect to the provider e retrieve information.

        Returns:
            bool: True if the operation succeeded. False otherwise.

        """
        success = True
        self.project = Project(name=self.project_id, iaas_uuid=self.project_id)
        try:
            self.quotas = self.get_quotas()
            self.storage_classes = self.get_storage_classes()
        except ApiException as e:
            success = False
            if e.status == 403:
                data = json.loads(e.body)
                self.logger.error("%s", data["message"])
            else:
                self.logger.error("Error occurred when retrieving quotas: %s", e)
            self.logger.error("Connection aborted. Skipping project")
        except urllib3.exceptions.MaxRetryError as e:
            success = False
            self.logger.error("%s", e._message)
            self.logger.error("Connection aborted. Skipping project")

        return success

    def split_quotas(
        self, key: str, value: str, data: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """Create dict with quotas keys."""
        if key == "cpu" or key == "memory":
            key = f"requests.{key}"
        if key == "persistentvolumeclaims":
            key = "pvcs"
        if key == "requests.storage":
            key = "storage"
        key = key.replace(".", "_")
        key = key.replace("-", "_")

        if value.endswith("Gi"):
            value = value[:-2]

        if key in [
            "limits_cpu",
            "limits_memory",
            "requests_cpu",
            "requests_memory",
            "pods",
        ]:
            data["compute"][key] = int(value)
        elif key in [
            "requests_ephemeral_storage",
            "limits_ephemeral_storage",
            "storage",
            "pvcs",
        ]:
            data["block_storage"][key] = int(value)
        elif key in []:
            data["storage_class"][key] = int(value)

        return data

    def get_quotas(self) -> list[ComputeQuota | BlockStorageQuota]:
        """Retrieve quotas."""
        quotas = {"compute": {}, "block_storage": {}, "storage_class": {}}
        usage = {"compute": {}, "block_storage": {}, "storage_class": {}}

        resource_quotas = self.corev1.list_namespaced_resource_quota(
            namespace=self.project_id, _request_timeout=self.timeout
        )
        for quota in resource_quotas.items:
            self.logger.debug("Quotas:")
            for resource, value in quota.status.hard.items():
                self.logger.debug("  %s: %s - %s", resource, value, type(value))
                quotas = self.split_quotas(resource, value, quotas)

            self.logger.debug("Usage:")
            for resource, value in quota.status.used.items():
                self.logger.debug("  %s: %s - %s", resource, value, type(value))
                usage = self.split_quotas(resource, value, usage)

        compute_quota = ComputeQuota(**quotas["compute"])
        compute_usage = ComputeQuota(**usage["compute"], usage=True)
        block_storage_quota = BlockStorageQuota(**quotas["block_storage"])
        block_storage_usage = BlockStorageQuota(**usage["block_storage"], usage=True)
        # storage_class_quota = StorageClassQuota(
        #     **quotas["storage_class"]
        # )
        # storage_class_usage = StorageClassQuota(
        #     **usage["storage_class"], usage=True
        # )
        return [compute_quota, compute_usage, block_storage_quota, block_storage_usage]

    def get_storage_classes(self) -> list[StorageClass]:
        """Retrieve available storage classes."""
        storage_class_list = []
        storage_classes = self.storagev1.list_storage_class(
            _request_timeout=self.timeout
        )
        for storage_class in storage_classes.items:
            data = {
                "name": storage_class.metadata.name,
                "is_default": storage_class.metadata.annotations.get(
                    "storageclass.kubernetes.io/is-default-class", False
                ),
                "provisioner": storage_class.provisioner,
            }
            storage_class_list.append(StorageClass(**data))
        return storage_class_list
