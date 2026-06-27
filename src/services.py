from typing import TYPE_CHECKING

from scope import osgi

BUNDLE_CONTEXT = osgi.bundleContext

if TYPE_CHECKING:
    from org.osgi.framework import ServiceReference
    from typing import overload, TypeVar

    T = TypeVar('T')

    @overload
    def getService(class_or_name: type[T] ) -> T: ...

    @overload
    def getService(class_or_name ) -> ServiceReference: ...

    @overload
    def findService(class_name, service_filter) -> list[ServiceReference]: ...

def getService(class_or_name):
    if BUNDLE_CONTEXT:
        classname = class_or_name.getName() if isinstance(class_or_name, type) else class_or_name
        ref = BUNDLE_CONTEXT.getServiceReference(classname)
        return BUNDLE_CONTEXT.getService(ref) if ref else None
    else:
        return None

def findService(class_name, service_filter):
    if BUNDLE_CONTEXT:
        references = BUNDLE_CONTEXT.getServiceReferences(class_name, service_filter)
        if references:
            return [BUNDLE_CONTEXT.getService(reference) for reference in references]
        else:
            return []
    else:
        return None
