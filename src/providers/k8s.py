import json
from logging import Logger
from typing import Any

import urllib3
from fedreg.project.schemas import ProjectCreate
from fedreg.provider.schemas_extended import (
    BlockStorageQuotaCreateExtended,
    BlockStorageServiceCreateExtended,
    ComputeQuotaCreateExtended,
    ComputeServiceCreateExtended,
    StorageClassCreateExtended,
    StorageClassQuotaCreateExtended,
)
from fedreg.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    IdentityServiceName,
)
from fedreg.service.schemas import IdentityServiceCreate
from kubernetes.client.exceptions import ApiException

from kubernetes import client
from src.models.identity_provider import Issuer, retrieve_token
from src.models.provider import Kubernetes

REQUEST_TIMEOUT = 2


class KubernetesProviderError(Exception):
    """Raised when data retrieval from an kubernetes provider fails."""


class KubernetesData:
    """Class to organize data retrieved from and Kubernetes instance."""

    def __init__(self, *, provider_conf: Kubernetes, issuer: Issuer, logger: Logger):
        self.error = False
        self.logger = logger
        try:
            assert len(provider_conf.regions) == 1, (
                f"Invalid number or regions: {len(provider_conf.regions)}"
            )
            assert len(provider_conf.projects) == 1, (
                f"Invalid number or projects: {len(provider_conf.projects)}"
            )
            msg = "Invalid number or trusted identity providers: "
            msg += f"{len(provider_conf.identity_providers)}"
            assert len(provider_conf.identity_providers) == 1, msg

            self.provider_conf = provider_conf
            self.project_conf = provider_conf.projects[0]
            self.auth_method = provider_conf.identity_providers[0]
            self.region_name = provider_conf.regions[0].name
            self.issuer = issuer

            self.project = None
            self.block_storage_services = []
            self.compute_services = []
            self.identity_services = []
            self.network_services = []
            self.object_store_services = []

            ssl_ca_cert_path = None

            # Connection is only defined, not yet opened
            self.client = self.create_connection(
                token=retrieve_token(
                    self.issuer.endpoint, audience=self.auth_method.audience
                ),
                ssl_ca_cert_path=ssl_ca_cert_path,
            )

            self.corev1 = client.CoreV1Api(self.client)
            self.storagev1 = client.StorageV1Api(self.client)

            # Retrieve information
            self.retrieve_info()
        except AssertionError as e:
            self.error = True
            self.logger.error(e)
            raise KubernetesProviderError from e

    def to_dict(self) -> dict:
        return {
            "provider_conf": self.provider_conf.dict(),
            "issuer": self.issuer.dict(),
            "project": self.project.dict(),
            "block_storage_services": [i.dict() for i in self.block_storage_services],
            "compute_services": [i.dict() for i in self.compute_services],
            "identity_services": [i.dict() for i in self.identity_services],
            "network_services": [i.dict() for i in self.network_services],
            "object_store_services": [i.dict() for i in self.object_store_services],
        }

    def create_connection(
        self, *, token: str, ssl_ca_cert_path: str
    ) -> client.ApiClient:
        """Create a connection with the k8s cluster's V1 API."""
        conf = client.Configuration(
            host=self.provider_conf.auth_url,
            api_key={"authorization": token},
            api_key_prefix={"authorization": "Bearer"},
        )
        conf.ssl_ca_cert = ssl_ca_cert_path
        return client.ApiClient(conf)

    def retrieve_info(self):
        self.project = ProjectCreate(
            name=self.project_conf.id, uuid=self.project_conf.id
        )
        self.identity_services = [
            IdentityServiceCreate(
                endpoint=self.provider_conf.auth_url,
                name=IdentityServiceName.KUBERNETES,
            )
        ]
        try:
            block_storage_service, compute_service = self.get_services()
            self.block_storage_services.append(block_storage_service)
            self.compute_services.append(compute_service)
        except ApiException as e:
            self.error = True
            if e.status == 403:
                data = json.loads(e.body)
                self.logger.error("%s", data["message"])
            else:
                self.logger.error("Error occurred when retrieving quotas: %s", e)
        except urllib3.exceptions.MaxRetryError as e:
            self.error = True
            self.logger.error("%s", e._message)

    def get_storage_classes(self) -> list[StorageClassCreateExtended]:
        storage_class_list = []
        storage_classes = self.storagev1.list_storage_class(
            _request_timeout=REQUEST_TIMEOUT
        )
        for storage_class in storage_classes.items:
            data = {
                "name": storage_class.metadata.name,
                "is_default": storage_class.metadata.annotations.get(
                    "storageclass.kubernetes.io/is-default-class", False
                ),
                "provisioner": storage_class.provisioner,
            }
            storage_class_list.append(StorageClassCreateExtended(**data))
        return storage_class_list

    def split_quotas(
        self, key: str, value: str, data: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
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

    def get_quotas(
        self,
    ) -> tuple[
        ComputeQuotaCreateExtended,
        ComputeQuotaCreateExtended,
        BlockStorageQuotaCreateExtended,
        BlockStorageQuotaCreateExtended,
        StorageClassQuotaCreateExtended,
        StorageClassQuotaCreateExtended,
    ]:
        compute_quota = {}
        compute_usage = {}
        block_storage_quota = {}
        block_storage_usage = {}
        # storage_class_quota = {}
        # storage_class_usage = {}

        quotas = {"compute": {}, "block_storage": {}, "storage_class": {}}
        usage = {"compute": {}, "block_storage": {}, "storage_class": {}}

        resource_quotas = self.corev1.list_namespaced_resource_quota(
            namespace=self.project_conf.id, _request_timeout=REQUEST_TIMEOUT
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

        compute_quota = ComputeQuotaCreateExtended(
            **quotas["compute"], project=self.project_conf.id
        )
        compute_usage = ComputeQuotaCreateExtended(
            **usage["compute"], project=self.project_conf.id, usage=True
        )
        block_storage_quota = BlockStorageQuotaCreateExtended(
            **quotas["block_storage"], project=self.project_conf.id
        )
        block_storage_usage = BlockStorageQuotaCreateExtended(
            **usage["block_storage"], project=self.project_conf.id, usage=True
        )
        # storage_class_quota = StorageClassQuotaCreateExtended(
        #     **quotas["storage_class"], project=self.project_conf.id
        # )
        # storage_class_usage = StorageClassQuotaCreateExtended(
        #     **usage["storage_class"], project=self.project_conf.id, usage=True
        # )
        return (
            compute_quota,
            compute_usage,
            block_storage_quota,
            block_storage_usage,
            # storage_class_quota,
            # storage_class_usage,
        )

    def get_services(
        self,
    ) -> tuple[BlockStorageServiceCreateExtended, ComputeServiceCreateExtended]:
        (
            compute_quota,
            compute_usage,
            block_storage_quota,
            block_storage_usage,
            # storage_class_quota,
            # storage_class_usage,
        ) = self.get_quotas()

        storage_classes = self.get_storage_classes()

        block_storage_service = BlockStorageServiceCreateExtended(
            endpoint=f"{self.provider_conf.auth_url}/{BlockStorageServiceName.KUBERNETES.value}",
            name=BlockStorageServiceName.KUBERNETES,
            quotas=[block_storage_quota, block_storage_usage],
            storage_classes=storage_classes,
        )
        if self.project_conf.per_user_limits.block_storage:
            block_storage_service.quotas.append(
                BlockStorageQuotaCreateExtended(
                    **self.project_conf.per_user_limits.block_storage.dict(
                        exclude_none=True
                    ),
                    project=self.project_conf.id,
                )
            )

        compute_service = ComputeServiceCreateExtended(
            endpoint=f"{self.provider_conf.auth_url}/{ComputeServiceName.KUBERNETES.value}",
            name=ComputeServiceName.KUBERNETES,
            quotas=[compute_quota, compute_usage],
        )
        if self.project_conf.per_user_limits.compute:
            compute_service.quotas.append(
                ComputeQuotaCreateExtended(
                    **self.project_conf.per_user_limits.compute.dict(exclude_none=True),
                    project=self.project_conf.id,
                )
            )

        return block_storage_service, compute_service
