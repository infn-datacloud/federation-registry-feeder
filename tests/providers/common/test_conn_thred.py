from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING
from typing import Literal

import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import AuthMethod, Openstack, Project, Region
from src.providers.conn_thread import ConnectionThread
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    openstack_dict,
    project_dict,
    region_dict,
    sla_dict,
    user_group_dict,
)
from tests.utils import random_lower_string


class CaseProvider:
    def case_openstack(self) -> Openstack:
        return Openstack(
            **openstack_dict(),
            identity_providers=[auth_method_dict()],
            projects=[project_dict()],
        )


class CaseLoggingLevel:
    def case_none(self) -> None:
        return None

    @parametrize(level=(CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING))
    def case_level(self, level: int) -> int:
        return level


class CaseInvalidNum:
    def case_0(self) -> Literal[0]:
        return 0

    def case_2(self) -> Literal[2]:
        return 2


@parametrize_with_cases("provider_conf", cases=CaseProvider)
@parametrize_with_cases("level", cases=CaseLoggingLevel)
def test_connection_thread_creation(provider_conf: Openstack, level: int | None):
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
    )
    issuer.endpoint = provider_conf.identity_providers[0].endpoint

    item = ConnectionThread(provider_conf=provider_conf, issuer=issuer, log_level=level)
    assert item.provider_conf == provider_conf
    assert item.issuer == issuer
    assert item.logger is not None
    if level is None:
        assert item.logger.level == NOTSET
    else:
        assert item.logger.level == level
    assert not item.error


@parametrize_with_cases("provider_conf", cases=CaseProvider)
def test_not_matching_idp_endpoints(provider_conf: Openstack, level: int | None):
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
    )

    msg = f"Issuer endpoint {issuer.endpoint} does not match trusted identity "
    msg += f"provider's one {provider_conf.identity_providers[0].endpoint}"
    with pytest.raises(AssertionError, match=msg):
        ConnectionThread(provider_conf=provider_conf, issuer=issuer, log_level=level)


@parametrize_with_cases("provider_conf", cases=CaseProvider)
@parametrize_with_cases("num", cases=CaseInvalidNum)
def test_invalid_num_regions(provider_conf: Openstack, num: int):
    if num == 0:
        provider_conf.regions.clear()
    else:
        provider_conf.regions.append(Region(**region_dict()))
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
    )
    issuer.endpoint = provider_conf.identity_providers[0].endpoint

    with pytest.raises(AssertionError, match=f"Invalid number of regions: {num}"):
        ConnectionThread(provider_conf=provider_conf, issuer=issuer, log_level=None)


@parametrize_with_cases("provider_conf", cases=CaseProvider)
@parametrize_with_cases("num", cases=CaseInvalidNum)
def test_invalid_num_projects(provider_conf: Openstack, num: int):
    if num == 0:
        provider_conf.projects.clear()
    else:
        provider_conf.projects.append(Project(**project_dict()))
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
    )
    issuer.endpoint = provider_conf.identity_providers[0].endpoint

    with pytest.raises(AssertionError, match=f"Invalid number of projects: {num}"):
        ConnectionThread(provider_conf=provider_conf, issuer=issuer, log_level=None)


@parametrize_with_cases("provider_conf", cases=CaseProvider)
@parametrize_with_cases("num", cases=CaseInvalidNum)
def test_invalid_num_idps(provider_conf: Openstack, num: int):
    if num == 0:
        provider_conf.identity_providers.clear()
    else:
        provider_conf.identity_providers.append(AuthMethod(**auth_method_dict()))
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
    )

    with pytest.raises(
        AssertionError, match=f"Invalid number of trusted identity providers: {num}"
    ):
        ConnectionThread(provider_conf=provider_conf, issuer=[issuer], log_level=None)


@parametrize_with_cases("provider_conf", cases=CaseProvider)
@parametrize_with_cases("num", cases=CaseInvalidNum)
def test_invalid_num_user_groups(provider_conf: Openstack, num: int):
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
    )
    issuer.endpoint = provider_conf.identity_providers[0].endpoint
    if num == 0:
        issuer.user_groups.clear()
    else:
        issuer.user_groups.append(
            UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])
        )

    with pytest.raises(AssertionError, match=f"Invalid number of user groups: {num}"):
        ConnectionThread(provider_conf=provider_conf, issuer=issuer, log_level=None)


@parametrize_with_cases("provider_conf", cases=CaseProvider)
@parametrize_with_cases("num", cases=CaseInvalidNum)
def test_invalid_num_slas(provider_conf: Openstack, num: int):
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
    )
    issuer.endpoint = provider_conf.identity_providers[0].endpoint
    if num == 0:
        issuer.user_groups[0].slas.clear()
    else:
        issuer.user_groups[0].slas.append(SLA(**sla_dict()))

    with pytest.raises(AssertionError, match=f"Invalid number of slas: {num}"):
        ConnectionThread(provider_conf=provider_conf, issuer=issuer, log_level=None)
