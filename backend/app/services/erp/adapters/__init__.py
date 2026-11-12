from typing import Dict, Type
from app.services.erp.adapters.base import ERPAdapterInterface
from app.services.erp.adapters.mock_erp import MockUniversityERPAdapter
from app.services.erp.adapters.sap import SAPAdapter
from app.services.erp.adapters.oracle import OracleERPAdapter
from app.services.erp.adapters.generic_rest import GenericRESTAdapter

_ADAPTER_REGISTRY: Dict[str, Type[ERPAdapterInterface]] = {
    "MOCK_UNIVERSITY_ERP": MockUniversityERPAdapter,
    "MOCK": MockUniversityERPAdapter,
    "SAP": SAPAdapter,
    "ORACLE": OracleERPAdapter,
    "GENERIC_REST": GenericRESTAdapter,
}

_ACTIVE_ADAPTER_INSTANCES: Dict[str, ERPAdapterInterface] = {}


def get_erp_adapter(adapter_name: str = "MOCK_UNIVERSITY_ERP") -> ERPAdapterInterface:
    """Returns singleton instance of requested ERP adapter."""
    clean_name = adapter_name.upper().strip()
    if clean_name not in _ADAPTER_REGISTRY:
        clean_name = "MOCK_UNIVERSITY_ERP"

    if clean_name not in _ACTIVE_ADAPTER_INSTANCES:
        adapter_cls = _ADAPTER_REGISTRY[clean_name]
        _ACTIVE_ADAPTER_INSTANCES[clean_name] = adapter_cls()

    return _ACTIVE_ADAPTER_INSTANCES[clean_name]
