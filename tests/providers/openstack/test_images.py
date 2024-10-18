from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fed_reg.provider.schemas_extended import ImageCreateExtended
from openstack.image.v2.image import Image
from openstack.image.v2.member import Member
from pytest_cases import case, parametrize, parametrize_with_cases
from pytest_cases import filters as ft

from src.providers.openstack import OpenstackData
from tests.providers.openstack.utils import (
    filter_item_by_tags,
    openstack_image_dict,
    random_image_status,
)


class CaseTaglist:
    @case(tags="empty")
    def case_empty_tag_list(self) -> list:
        return []

    @case(tags="empty")
    def case_no_list(self) -> None:
        return None

    @case(tags="not-empty")
    def case_one_item(self) -> list[str]:
        return ["one"]

    @case(tags="not-empty")
    def case_two_items(self) -> list[str]:
        return ["one", "two"]


class CaseAcceptStatus:
    @parametrize(acceptance_status=["accepted", "rejected", "pending"])
    def case_acceptance_status(self, acceptance_status: bool) -> bool:
        return acceptance_status


class CaseOpenstackImage:
    @case(tags="public")
    def case_image_disabled(self) -> Image:
        """Fixture with disabled image."""
        d = openstack_image_dict()
        d["status"] = random_image_status(exclude=["active"])
        return Image(**d)

    @case(tags="public")
    @parametrize(tags=(["one"], ["two"], ["one-two"], ["one", "two"]))
    def case_image_with_tags(self, tags: list[str]) -> Image:
        """Fixture with image with specified tags."""
        d = openstack_image_dict()
        d["tags"] = tags
        return Image(**d)

    @case(tags="public")
    @parametrize(visibility=("public", "community"))
    def case_image_public(self, visibility: str) -> Image:
        """Fixture with image with specified visibility."""
        d = openstack_image_dict()
        d["visibility"] = visibility
        return Image(**d)

    @case(tags="private")
    def case_image_private(self) -> Image:
        """Fixture with private image."""
        d = openstack_image_dict()
        d["visibility"] = "private"
        return Image(**d)

    @case(tags="shared")
    def case_image_shared(self) -> Image:
        """Fixture with private image."""
        d = openstack_image_dict()
        d["visibility"] = "shared"
        return Image(**d)


@patch("src.providers.openstack.Connection.image")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("openstack_image", cases=CaseOpenstackImage, has_tag="public")
@parametrize_with_cases("tags", cases=CaseTaglist, has_tag="empty")
def test_retrieve_public_images(
    mock_conn: Mock,
    mock_image: Mock,
    openstack_image: Image,
    openstack_item: OpenstackData,
    tags: list[str] | None,
) -> None:
    """Successful retrieval of an Image.

    Retrieve only active images and with the tags contained in the target tags list.
    If the target tags list is empty or None, all active images are valid ones.

    Images retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    images = [openstack_image]
    mock_image.images.return_value = images
    mock_conn.image = mock_image
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data = openstack_item.get_images(tags=tags)
    assert len(data) == len(images)
    if len(data) > 0:
        item = data[0]
        assert isinstance(item, ImageCreateExtended)
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
@parametrize_with_cases("tags", cases=CaseTaglist, has_tag="not-empty")
def test_tags_filter(
    mock_conn: Mock,
    mock_image: Mock,
    openstack_item: OpenstackData,
    tags: list[str],
) -> None:
    """Successful retrieval of an Image.

    Retrieve only active images and with the tags contained in the target tags list.
    If the target tags list is empty or None, all active images are valid ones.

    Images retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    openstack_image1 = Image(**openstack_image_dict())
    openstack_image1.tags = ["one", "two"]
    openstack_image2 = Image(**openstack_image_dict())
    openstack_image2.tags = ["one-two"]

    images = list(
        filter(
            lambda x: filter_item_by_tags(x, tags) and x.status == "active",
            [openstack_image1, openstack_image2],
        )
    )
    mock_image.images.return_value = images
    mock_conn.image = mock_image
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data = openstack_item.get_images(tags=tags)
    assert len(data) == 1
    item = data[0]
    assert len(set(tags).intersection(set(item.tags)))


@patch("src.providers.openstack.Connection.image.members")
@patch("src.providers.openstack.Connection.image")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("openstack_image", cases=CaseOpenstackImage, has_tag="shared")
@parametrize_with_cases("acceptance_status", cases=CaseAcceptStatus)
def test_retrieve_shared_image_projects(
    mock_conn: Mock,
    mock_image: Mock,
    mock_members: Mock,
    openstack_image: Image,
    openstack_item: OpenstackData,
    acceptance_status: str,
) -> None:
    """Owner does not appear in shared images"""
    project_id = uuid4().hex
    members = [Member(status=acceptance_status, id=project_id)]
    mock_members.return_value = members
    mock_image.members = mock_members
    mock_conn.image = mock_image
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data = openstack_item.get_image_projects(openstack_image)
    if acceptance_status == "accepted":
        assert len(data) == 2
        assert openstack_image.owner_id in data
        assert project_id in data
    else:
        assert len(data) == 1
        assert data[0] == openstack_image.owner_id


@patch("src.providers.openstack.OpenstackData.get_image_projects")
@patch("src.providers.openstack.Connection.image")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases(
    "openstack_image",
    cases=CaseOpenstackImage,
    filter=ft.has_tag("shared") | ft.has_tag("private"),
)
def test_retrieve_private_images(
    mock_conn: Mock,
    mock_image: Mock,
    mock_image_projects: Mock,
    openstack_image: Image,
    openstack_item: OpenstackData,
) -> None:
    """Successful retrieval of an Image with a specified visibility.

    Check that the is_public flag is correctly set to False and projects list is
    correct.
    """
    openstack_image.owner_id = openstack_item.project_conf.id
    images = [openstack_image]
    mock_image_projects.return_value = [openstack_item.project_conf.id]
    mock_image.images.return_value = images
    mock_conn.image = mock_image
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data = openstack_item.get_images()
    assert len(data) == len(images)
    item = data[0]
    assert isinstance(item, ImageCreateExtended)
    assert not item.is_public
    assert item.projects[0] == openstack_item.project_conf.id
