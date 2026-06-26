from typing import Literal, TypeVar, overload

from org.openhab.core.automation import RuleManager
from scope import osgi


BUNDLE_CONTEXT = osgi.bundleContext

@overload
def getService(class_or_name: Literal['org.openhab.core.automation.RuleManager']) -> RuleManager: ...

Java_ServiceReference = TypeVar("org.osgi.framework.ServiceReference")
def getService(class_or_name) -> Java_ServiceReference:
    if BUNDLE_CONTEXT:
        classname = class_or_name.getName() if isinstance(class_or_name, type) else class_or_name
        ref = BUNDLE_CONTEXT.getServiceReference(classname)
        return BUNDLE_CONTEXT.getService(ref) if ref else None
    else:
        return None

def findService(class_name, service_filter) -> list[Java_ServiceReference]:
    if BUNDLE_CONTEXT:
        references = BUNDLE_CONTEXT.getServiceReferences(class_name, service_filter)
        if references:
            return [BUNDLE_CONTEXT.getService(reference) for reference in references]
        else:
            return []
    else:
        return None
