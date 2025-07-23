def __import_wrapper__():
    from polyglot import register_interop_type
    from java.lang import Object as Java_Object

    import builtins
    import types
    import sys
    import java
    import os
    import traceback

    importOrg = builtins.__import__

    class WrappedException(Exception):
        def __init__(self, exception, skip):
            self.exception = exception
            self.skip = skip

    class Module(types.ModuleType):
        def __init__(self, name, modules):
            super().__init__(name)
            self.__all__ = list(modules.keySet() if hasattr(modules, 'keySet') else modules.keys() )
            for k in self.__all__:
                if hasattr(modules[k], 'getClass') and modules[k].getClass().getName() == "java.util.HashMap":
                    modules[k] = Module(k, modules[k])
                setattr(self, k, modules[k])

    def processModules(name, fromlist, modules):
        if modules:
            return Module(name, modules)
        msg = "No module named '{}{}'".format(name, '.' + '|'.join(fromlist) if fromlist else "")
        raise WrappedException(ModuleNotFoundError(msg), 2)

    def getImportProxy():
        depth = 1
        while True:
            try:
                frame = sys._getframe(depth)
                if '__import_proxy__' in frame.f_globals:
                    return frame.f_globals['__import_proxy__']
                depth += 1
            except ValueError:
                raise EnvironmentError("No __import_proxy__ is available")

    importProxy = getImportProxy()
    def importWrapper(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("org.openhab"):
            modules = {}
            _modules = importProxy(name, fromlist)
            for _name in _modules['class_list']:
                try:
                    modules[_name.split(".")[-1]] = java.type(_name)
                except KeyError as e:
                    raise WrappedException(ModuleNotFoundError("Class '{}' not found".format(_name)), 1)
            return processModules(name, fromlist, modules)
        if name.startswith("scope"):
            modules = importProxy(name, fromlist)
            return processModules(name, fromlist, modules)
        return importOrg(name, globals, locals, fromlist, level)
    builtins.__import__ = importWrapper

    def excepthook(exctype, excvalue, tb):
        _tb_r = []
        for _tb in traceback.extract_tb(tb):
            _tb_r.append(_tb)

        if isinstance(excvalue, WrappedException):
            _tb_r = _tb_r [0:(excvalue.skip*-1)]
            excvalue = excvalue.exception
            exctype = excvalue.__class__

        result_r = []
        result_r.append("{}, {}".format(exctype.__name__, excvalue))
        result_r.append("Traceback (most recent call last):")
        for line in traceback.format_list(_tb_r):
            result_r.append(line.strip())

        print("\n".join(result_r), file=sys.stderr)
    sys.excepthook = excepthook

    # Replace error messages
    # => old: "AttributeError, foreign object has no attribute 'test'"
    # => new: "AttributeError, Java instance of 'org.openhab.core.types.UnDefType' has not attribute 'test'"
    class CustomForeignClass:
        def __getattr__(self, name):
            raise WrappedException(AttributeError("Java instance of '{}' has not attribute '{}'".format(self.getClass(), name)), 1)
    register_interop_type(Java_Object, CustomForeignClass)
__import_wrapper__()
