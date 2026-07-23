# gather/contrib/sites/test_migrations.py
import importlib

module = importlib.import_module(
    "gather.contrib.sites.migrations.0003_set_site_domain_and_name",
)
_update_or_create_site_with_sequence = module._update_or_create_site_with_sequence  # noqa: SLF001


def test_update_or_create_site_skips_sequence_sync_on_sqlite():
    class FakeSite:
        id = 1

    class FakeObjects:
        def update_or_create(self, **kwargs):
            return FakeSite(), True

        def order_by(self, *_args, **_kwargs):
            return self

        def first(self):
            return FakeSite()

    class FakeSiteModel:
        objects = FakeObjects()

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *_args, **_kwargs):
            message = "sequence sync should not run on sqlite"
            raise AssertionError(message)

    class FakeConnection:
        vendor = "sqlite"

        def cursor(self):
            return FakeCursor()

    _update_or_create_site_with_sequence(
        FakeSiteModel,
        FakeConnection(),
        "example.com",
        "Example",
    )
