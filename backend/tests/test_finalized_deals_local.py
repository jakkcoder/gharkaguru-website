"""Finalized deals work without GCS when SKIP_GCS_SYNC is set (home server)."""
import importlib

from fastapi.testclient import TestClient


def test_finalized_deals_page_without_gcs(tmp_path, monkeypatch):
    monkeypatch.setenv("SKIP_GCS_SYNC", "true")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import app.config, app.finalized_deals_db, app.finalized_deals_routes, app.main
    for m in (app.config, app.finalized_deals_db, app.finalized_deals_routes, app.main):
        importlib.reload(m)
    import app.finalized_deals_gcs as g
    monkeypatch.setattr(g, "_client", lambda: (_ for _ in ()).throw(AssertionError("GCS must not be used")))
    c = TestClient(app.main.app)
    r = c.post("/finilized_deals/login", data={"password": app.config.FINALIZED_DEALS_PASSWORD}, follow_redirects=False)
    assert r.status_code == 303
    page = c.get("/finilized_deals")
    assert page.status_code == 200
