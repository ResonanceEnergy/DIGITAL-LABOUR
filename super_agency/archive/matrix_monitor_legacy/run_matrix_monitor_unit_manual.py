import sys
import importlib.util
# ensure workspace root is on PYTHONPATH
sys.path.insert(0, '.')
# load unit test module from file since tests/ is not a package
spec = importlib.util.spec_from_file_location('tm', 'tests/test_matrix_monitor_unit.py')
module = importlib.util.module_from_spec(spec)
sys.modules['tm'] = module
spec.loader.exec_module(module)
# alias for convenience
tm = module
print('running unit tests manually')

# crude monkeypatch implementation for manual invocation
class DummyMonkeyPatch:
    def setattr(self, target, value, raising=True):
        # target string like 'module.attr'
        parts = target.split('.')
        module = __import__('.'.join(parts[:-1]), fromlist=[parts[-1]])
        setattr(module, parts[-1], value)

mp = DummyMonkeyPatch()

for fn in [tm.test_matrix_monitor_success, tm.test_matrix_monitor_partial_failures, tm.test_route_client, tm.test_cache_behavior]:
    try:
        # pass dummy monkeypatch where needed
        fn(mp)
        print(fn.__name__, 'passed')
    except Exception as e:
        print(fn.__name__, 'failed', e)
        import traceback; traceback.print_exc()
