def test_packages_import():
    import app
    import etl
    import scripts

    assert all(m is not None for m in (app, etl, scripts))
