from typing import Any, Dict, List, Optional
from unittest.mock import patch
from uuid import uuid4

import pytest
from openstack.image.v2.image import Image
from openstack.image.v2.member import Member
from pytest_cases import case, parametrize, parametrize_with_cases

from src.providers.openstack import get_images
from tests.openstack.utils import random_image_status, random_image_visibility
from tests.schemas.utils import random_image_os_type, random_lower_string


# `shared` has a separate case
@case(tags=["visibility"])
@parametrize(visibility=["public", "private", "community"])
def case_visibility(visibility: bool) -> bool:
    return visibility


@case(tags=["tags"])
@parametrize(tags=range(4))
def case_tags(tags: int) -> List[str]:
    if tags == 0:
        return ["one"]
    if tags == 1:
        return ["two"]
    if tags == 2:
        return ["one", "two"]
    if tags == 3:
        return ["one-two"]


@case(tags=["no_tags"])
@parametrize(empty_list=[True, False])
def case_empty_tag_list(empty_list: bool) -> Optional[List]:
    return [] if empty_list else None


@case(tags=["acceptance_status"])
@parametrize(acceptance_status=["accepted", "rejected", "pending"])
def case_acceptance_status(acceptance_status: bool) -> bool:
    return acceptance_status


def image_data() -> Dict[str, Any]:
    return {
        "id": uuid4().hex,
        "name": random_lower_string(),
        "status": "active",
        "owner": uuid4().hex,
        "os_type": random_image_os_type(),
        "os_distro": random_lower_string(),
        "os_version": random_lower_string(),
        "architecture": random_lower_string(),
        "kernel_id": random_lower_string(),
        "visibility": random_image_visibility(),
    }


@pytest.fixture
def image_disabled() -> Image:
    d = image_data()
    d["status"] = random_image_status(exclude=["active"])
    return Image(**d)


@pytest.fixture
@parametrize_with_cases("visibility", cases=".", has_tag="visibility")
def image_visible(visibility: str) -> Image:
    d = image_data()
    d["visibility"] = visibility
    return Image(**d)


@pytest.fixture
@parametrize_with_cases("tags", cases=".", has_tag="tags")
def image_with_tags(tags: List[str]) -> Image:
    d = image_data()
    d["tags"] = tags
    return Image(**d)


@pytest.fixture
def image_shared() -> Image:
    d = image_data()
    d["visibility"] = "shared"
    return Image(**d)


@pytest.fixture
@parametrize(i=[image_disabled, image_visible])
def image(i: Image) -> Image:
    return i


@patch("src.providers.openstack.Connection.image")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("tags", cases=".", has_tag="no_tags")
def test_retrieve_images(
    mock_conn, mock_image, image: Image, tags: Optional[List]
) -> None:
    images = list(filter(lambda x: x.status == "active", [image]))
    mock_image.images.return_value = images
    mock_conn.image = mock_image
    data = get_images(mock_conn, tags=tags)

    assert len(data) == len(images)
    if len(data) > 0:
        item = data[0]
        assert item.description == ""
        assert item.uuid == image.id
        assert item.name == image.name
        assert item.os_type == image.os_type
        assert item.os_distro == image.os_distro
        assert item.os_version == image.os_version
        assert item.architecture == image.architecture
        assert item.kernel_id == image.kernel_id
        assert not item.cuda_support
        assert not item.gpu_driver
        assert item.tags == image.tags
        if image.visibility in ["private", "shared"]:
            assert not item.is_public
        else:
            assert item.is_public
        if item.is_public:
            assert len(item.projects) == 0
        else:
            assert len(item.projects) == len([image.owner_id])


@patch("src.providers.openstack.Connection.image")
@patch("src.providers.openstack.Connection")
def test_retrieve_images_with_tags(
    mock_conn, mock_image, image_with_tags: Image
) -> None:
    target_tags = ["one"]
    images = list(
        filter(lambda x: set(x.tags).intersection(set(target_tags)), [image_with_tags])
    )
    mock_image.images.return_value = images
    mock_conn.image = mock_image
    data = get_images(mock_conn, tags=target_tags)
    assert len(data) == len(images)


@patch("src.providers.openstack.Connection.image")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("acceptance_status", cases=".", has_tag="acceptance_status")
def test_retrieve_images_with_shared_visibility(
    mock_conn, mock_image, image_shared: Image, acceptance_status: str
) -> None:
    def get_allowed_members(*args, **kwargs) -> List[Member]:
        return [
            Member(status="accepted", id=image_shared.owner_id),
            Member(status=acceptance_status, id=uuid4().hex),
        ]

    images = [image_shared]
    mock_image.images.return_value = images
    mock_image.members.side_effect = get_allowed_members
    mock_conn.image = mock_image
    data = get_images(mock_conn)

    assert len(data) == len(images)
    if len(data) > 0:
        item = data[0]
        assert not item.is_public
        allowed_members = filter(
            lambda x: x.status == "accepted", get_allowed_members()
        )
        allowed_project_ids = set([i.id for i in allowed_members])
        allowed_project_ids.add(image_shared.owner_id)
        assert len(item.projects) == len(allowed_project_ids)
