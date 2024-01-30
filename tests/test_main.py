from unittest.mock import Mock, patch

from app.provider.schemas_extended import ProviderCreateExtended

from src.config import URLs
from src.main import main
from src.models.config import SiteConfig
from src.models.provider import Kubernetes, Openstack


@patch("src.main.update_database")
@patch("src.main.get_provider")
@patch("src.utils.load_config")
@patch("src.main.infer_service_endpoints")
def test_main(
    mock_infer_urls: Mock,
    mock_load_conf: Mock,
    mock_get_prov: Mock,
    mock_edit_db: Mock,
    service_endpoints: URLs,
    site_config: SiteConfig,
    openstack_provider: Openstack,
    kubernetes_provider: Kubernetes,
    provider_create: ProviderCreateExtended,
) -> None:
    site_config.openstack = [openstack_provider]
    site_config.kubernetes = [kubernetes_provider]

    mock_infer_urls.return_value = service_endpoints
    mock_load_conf.return_value = site_config
    mock_get_prov.return_value = provider_create
    mock_edit_db.return_value = None

    main()
