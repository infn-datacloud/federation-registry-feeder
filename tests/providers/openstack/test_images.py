from typing import List, Optional
from unittest.mock import Mock, patch
from uuid import uuid4

from openstack.image.v2.image import Image
from openstack.image.v2.member import Member
from pytest_cases import case, parametrize, parametrize_with_cases

from src.providers.openstack import get_images


class CaseTags:
    def case_single_valid_tag(self) -> List[str]:
        return ["one"]

    @parametrize(case=[0, 1])
    def case_single_invalid_tag(self, case: int) -> List[str]:
        return ["two"] if case else ["one-two"]

    def case_at_least_one_valid_tag(self) -> List[str]:
        return ["one", "two"]


class CaseTagList:
    @case(tags=["empty"])
    def case_empty_tag_list(self) -> Optional[List]:
        return []

    @case(tags=["empty"])
    def case_no_list(self) -> Optional[List]:
        return None

    @case(tags=["full"])
    def case_list(self) -> Optional[List]:
        return ["one"]


class CaseAcceptStatus:
    @parametrize(acceptance_status=["accepted", "rejected", "pending"])
    def case_acceptance_status(self, acceptance_status: bool) -> bool:
        return acceptance_status


def filter_images(image: Image, tags: Optional[List[str]]) -> bool:
    valid_tag = tags is None or len(tags) == 0
    if not valid_tag:
        valid_tag = len(set(image.tags).intersection(set(tags))) > 0
    return image.status == "active" and valid_tag


@patch("src.providers.openstack.Connection.image")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("tags", cases=CaseTagList)
def test_retrieve_public_images(
    mock_conn: Mock, mock_image: Mock, openstack_image: Image, tags: Optional[List[str]]
) -> None:
    """Successful retrieval of an Image.

    Retrieve only active images and with the tags contained in the target tags list.
    If the target tags list is empty or None, all active images are valid ones.

    Images retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    images = list(filter(lambda x: filter_images(x, tags), [openstack_image]))
    mock_image.images.return_value = images
    mock_conn.image = mock_image
    data = get_images(mock_conn, tags=tags)

    assert len(data) == len(images)
    if len(data) > 0:
        item = data[0]
        assert item.description == ""
        assert item.uuid == openstack_image.id
        assert item.name == openstack_image.name
        assert item.os_type == openstack_image.os_type
        assert item.os_distro == openstack_image.os_distro
        assert item.os_version == openstack_image.os_version
        assert item.architecture == openstack_image.architecture
        assert item.kernel_id == openstack_image.kernel_id
        assert not item.cuda_support
        assert not item.gpu_driver
        assert item.tags == openstack_image.tags
        assert item.is_public
        assert len(item.projects) == 0


@patch("src.providers.openstack.Connection.image")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("acceptance_status", cases=CaseAcceptStatus)
def test_retrieve_private_images(
    mock_conn: Mock,
    mock_image: Mock,
    openstack_image_private: Image,
    acceptance_status: str,
) -> None:
    """Successful retrieval of an Image with a specified visibility.

    Check that the is_public flag is correctly set to False and projects list is
    correct.
    """

    def get_allowed_members(*args, **kwargs) -> List[Member]:
        return [
            Member(status="accepted", id=openstack_image_private.owner_id),
            Member(status=acceptance_status, id=uuid4().hex),
        ]

    images = [openstack_image_private]
    mock_image.images.return_value = images
    mock_image.members.side_effect = get_allowed_members
    mock_conn.image = mock_image
    data = get_images(mock_conn)

    assert len(data) == len(images)
    assert not data[0].is_public
    if openstack_image_private.visibility == "private":
        allowed_project_ids = [openstack_image_private.owner_id]
    elif openstack_image_private.visibility == "shared":
        allowed_project_ids = list(
            filter(lambda x: x.status == "accepted", get_allowed_members())
        )
    assert len(data[0].projects) == len(allowed_project_ids)
