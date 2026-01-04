def __import_wrapper__():
    import java

    from java.util import HashMap as Java_HashMap

    import builtins
    import types
    import sys
    import traceback

    # **************** CATCH and PREPARE GRAAL EXCEPTIONS *********************
    def formatTraceback(excvalue):
        msg = str(excvalue)
        if msg == "invalid instantiation of foreign object":
            msg = "java object function parameters are missing or does not match the required value type"
        elif "foreign object" in msg:
            msg = msg.replace("foreign object", "java object")

        result_r = []
        result_r.append("{}, {}".format(type(excvalue).__name__, msg))

        _tb_r = []
        for _tb in traceback.extract_tb(excvalue.__traceback__):
            if _tb.name == "importWrapper": # hide wrapped import logic to keep focus on original import statement
                break
            _tb_r.append(_tb)

        if len(_tb_r) > 0:
            result_r.append("Traceback (most recent call last):")
            for line in traceback.format_list(_tb_r):
                result_r.append(line.strip())

        return "\n".join(result_r)

    builtins.__formatTraceback__ = formatTraceback

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
        modules = None
        if name.startswith("org.openhab"):
            modules = {}
            _modules = importProxy(name, fromlist)
            for _name in _modules['class_list']:
                try:
                    modules[_name.split(".")[-1]] = java.type(_name)
                except KeyError as e:
                    raise ModuleNotFoundError("Class '{}' not found".format(_name))
        elif name.startswith("scope"):
            modules = importProxy(name, fromlist)

        if modules is not None:
            if len(modules) > 0:
                return Module(name, modules)
            raise ModuleNotFoundError("No module named '{}{}'".format(name, '.' + '|'.join(fromlist) if fromlist else ""))

        return importOrg(name, globals, locals, fromlist, level)
    builtins.__import__ = importWrapper
    # **************************************************************************
__import_wrapper__()
