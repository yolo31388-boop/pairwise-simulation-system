"""pytest bootstrap: plain test classes in tests/ reuse unittest-style
assert* helpers without inheriting TestCase."""


def _assert_is_not_none(obj, msg=None):
    assert obj is not None, msg


def pytest_collection_modifyitems(items):
    patched = set()
    for item in items:
        cls = getattr(item, "cls", None)
        if cls is not None and id(cls) not in patched:
            patched.add(id(cls))
            if not hasattr(cls, "assertIsNotNone"):
                cls.assertIsNotNone = lambda self, obj, msg=None: _assert_is_not_none(
                    obj, msg
                )
