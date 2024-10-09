import logging
from unittest.mock import Mock, patch

from pytest_cases import parametrize_with_cases

from src.config import URLs
from src.main import main
from src.models.provider import Kubernetes, Openstack
from src.models.site_config import SiteConfig


class CaseSiteConfigs:
    def case_no_config(self) -> list[SiteConfig]:
        return []

    def case_one_config(
        self,
        site_config: SiteConfig,
        openstack_provider: Openstack,
        kubernetes_provider: Kubernetes,
    ) -> list[SiteConfig]:
        site_config.openstack = [openstack_provider]
        site_config.kubernetes = [kubernetes_provider]
        return [site_config]


@patch("src.main.update_database")
@patch("src.main.get_site_configs")
@patch("src.main.infer_service_endpoints")
@parametrize_with_cases("site_configs", cases=CaseSiteConfigs)
def test_main(
    mock_infer_urls: Mock,
    mock_load_conf: Mock,
    mock_edit_db: Mock,
    service_endpoints: URLs,
    site_configs: list[SiteConfig],
) -> None:
    """text the execution of the main function.

    If no exceptions or errors are raised, the main function should be executed till
    the end.
    """
    mock_infer_urls.return_value = service_endpoints
    mock_load_conf.return_value = site_configs
    mock_edit_db.return_value = None

    main(log_level=logging.INFO)

    mock_edit_db.assert_called_once()
