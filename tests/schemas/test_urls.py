import pytest
from pydantic import ValidationError
from pytest_cases import parametrize, parametrize_with_cases

from src.config import URLs
from tests.schemas.utils import urls_dict


class CaseMissingAttr:
    @parametrize(
        attr=(
            "flavors",
            "identity_providers",
            "images",
            "locations",
            "networks",
            "projects",
            "providers",
            "block_storage_quotas",
            "compute_quotas",
            "network_quotas",
            "object_store_quotas",
            "regions",
            "block_storage_services",
            "compute_services",
            "identity_services",
            "network_services",
            "slas",
            "user_groups",
        )
    )
    def case_attr(self, attr: str) -> str:
        return attr


def test_urls():
    d = urls_dict()
    urls = URLs(**d)
    assert urls.flavors == d.get("flavors")
    assert urls.identity_providers == d.get("identity_providers")
    assert urls.images == d.get("images")
    assert urls.locations == d.get("locations")
    assert urls.networks == d.get("networks")
    assert urls.projects == d.get("projects")
    assert urls.providers == d.get("providers")
    assert urls.block_storage_quotas == d.get("block_storage_quotas")
    assert urls.compute_quotas == d.get("compute_quotas")
    assert urls.network_quotas == d.get("network_quotas")
    assert urls.object_store_quotas == d.get("object_store_quotas")
    assert urls.regions == d.get("regions")
    assert urls.block_storage_services == d.get("block_storage_services")
    assert urls.compute_services == d.get("compute_services")
    assert urls.identity_services == d.get("identity_services")
    assert urls.network_services == d.get("network_services")
    assert urls.slas == d.get("slas")
    assert urls.user_groups == d.get("user_groups")


@parametrize_with_cases("key", cases=CaseMissingAttr)
def test_missing_attr(key: str):
    d = urls_dict()
    d.pop(key)
    with pytest.raises(ValidationError):
        URLs(**d)
