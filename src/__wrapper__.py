def __import_wrapper__():
    import java

    from polyglot import interop_type, ForeignNone
    from java.lang import Object as Java_Object
    from java.util import HashMap as Java_HashMap

    import builtins
    import types
    import sys
    import traceback

    # **************** CATCH and PREPARE GRAAL EXCEPTIONS *********************

    # used to mark the first 'skip' times of a traceback as not relevant
    # this are normally traceback frames of wrapped functions
    def wrapException(exception, skip):
        exception.__wrapExceptionTraceSkip = skip
        return exception

    # extract relevant traceback to keep focus on "real" error
    def extractTraceback(excvalue):
        _tb_r = []
        for _tb in traceback.extract_tb(excvalue.__traceback__):
            _tb_r.append(_tb)
        if hasattr(excvalue, "__wrapExceptionTraceSkip"):
            _tb_r = _tb_r [0:(excvalue.__wrapExceptionTraceSkip*-1)]
        return _tb_r

    def formatTraceback(excvalue):
        result_r = []
        result_r.append("{}, {}".format(type(excvalue).__name__, excvalue))

        _tb_r = extractTraceback(excvalue)
        if len(_tb_r) > 0:
            result_r.append("Traceback (most recent call last):")
            for line in traceback.format_list(_tb_r):
                result_r.append(line.strip())

        return "\n".join(result_r)

    builtins.__wrapException__ = wrapException
    builtins.__formatTraceback__ = formatTraceback

    # used for integration tests
    builtins.__validateException__ = lambda e, f: extractTraceback(e)[-1].filename == f

    sys.excepthook = lambda exctype, excvalue, tb: print(formatTraceback(excvalue), file=sys.stderr)
    # **************************************************************************

    # *************** IMPORT WRAPPER *******************************************
    class Module(types.ModuleType):
        def __init__(self, name, modules):
            super().__init__(name)
            self.__all__ = list(modules.keySet() if hasattr(modules, 'keySet') else modules.keys() )
            for k in self.__all__:
                if java.instanceof(modules[k], Java_HashMap):
                    modules[k] = Module(k, modules[k])
                setattr(self, k, modules[k])

    def processModules(name, fromlist, modules):
        if modules:
            return Module(name, modules)
        msg = "No module named '{}{}'".format(name, '.' + '|'.join(fromlist) if fromlist else "")
        raise wrapException(ModuleNotFoundError(msg), 2)

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

    importOrg = builtins.__import__
    importProxy = getImportProxy()
    def importWrapper(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("org.openhab"):
            modules = {}
            _modules = importProxy(name, fromlist)
            for _name in _modules['class_list']:
                try:
                    modules[_name.split(".")[-1]] = java.type(_name)
                except KeyError as e:
                    raise wrapException(ModuleNotFoundError("Class '{}' not found".format(_name)), 1)
            return processModules(name, fromlist, modules)
        if name.startswith("scope"):
            modules = importProxy(name, fromlist)
            return processModules(name, fromlist, modules)
        return importOrg(name, globals, locals, fromlist, level)
    builtins.__import__ = importWrapper
    # **************************************************************************
__import_wrapper__()
