"""Live web tests against Cloud Run parent_leads (admin + each agent id login)."""

from __future__ import annotations

import os
import re

import httpx
import pytest

CLOUD_BASE = os.getenv(
    "PARENT_LEADS_CLOUD_BASE_URL",
    "https://gharkaguru-website-lmquvtnfja-as.a.run.app",
)
ADMIN_PASSWORD = os.getenv("PARENT_LEADS_ADMIN_PASSWORD", "khus@123")
PREFIX = "/parent_leads"


def _parse_agents_table(html: str) -> list[dict[str, str]]:
    tbody = re.search(r"<tbody>(.*?)</tbody>", html, re.DOTALL)
    if not tbody:
        return []
    agents: list[dict[str, str]] = []
    for tr in re.findall(r"<tr>(.*?)</tr>", tbody.group(1), re.DOTALL):
        form_m = re.search(rf"{re.escape(PREFIX)}/admin/agents/([^/]+)/update", tr)
        if not form_m:
            continue
        tds = re.findall(r"<td>(.*?)</td>", tr, re.DOTALL)
        if len(tds) < 3:
            continue
        name = re.sub(r"<[^>]+>", "", tds[0]).strip()
        email = re.sub(r"<[^>]+>", "", tds[1]).strip()
        pwd_m = re.search(r"<code>([^<]*)</code>", tds[2])
        password = pwd_m.group(1).strip() if pwd_m else ""
        agents.append(
            {
                "id": form_m.group(1),
                "name": name,
                "email": email,
                "password": password,
            }
        )
    return agents


@pytest.fixture(scope="module")
def cloud_reachable() -> str:
    try:
        r = httpx.get(f"{CLOUD_BASE}/health", timeout=15.0)
    except httpx.HTTPError as exc:
        pytest.skip(f"Cloud Run unreachable: {exc}")
    if r.status_code != 200:
        pytest.skip(f"Cloud health returned {r.status_code}")
    return CLOUD_BASE


@pytest.fixture(scope="module")
def cloud_agents(cloud_reachable: str) -> list[dict[str, str]]:
    with httpx.Client(base_url=cloud_reachable, follow_redirects=True, timeout=90.0) as client:
        login = client.post(f"{PREFIX}/admin/login", data={"password": ADMIN_PASSWORD})
        assert login.status_code == 200
        html = client.get(f"{PREFIX}/admin/agents").text
        agents = _parse_agents_table(html)
        assert agents, "expected agents on admin page"
        return agents


def test_cloud_admin_agents_passwords_stable_after_refresh(cloud_reachable: str, cloud_agents: list):
    with httpx.Client(base_url=cloud_reachable, follow_redirects=True, timeout=90.0) as client:
        client.post(f"{PREFIX}/admin/login", data={"password": ADMIN_PASSWORD})
        first = _parse_agents_table(client.get(f"{PREFIX}/admin/agents").text)
        second = _parse_agents_table(client.get(f"{PREFIX}/admin/agents").text)
    assert len(first) == len(cloud_agents)
    for a in first:
        assert a["password"] and a["password"] != "—", a
    assert first == second


@pytest.mark.parametrize("agent_index", list(range(6)))
def test_cloud_each_agent_id_login_and_portal(
    cloud_reachable: str, cloud_agents: list, agent_index: int
):
    if agent_index >= len(cloud_agents):
        pytest.skip("agent index out of range")
    agent = cloud_agents[agent_index]
    assert agent["password"] and agent["password"] != "—"

    with httpx.Client(base_url=cloud_reachable, follow_redirects=False, timeout=90.0) as client:
        r = client.post(
            f"{PREFIX}/login",
            data={"email": agent["email"], "password": agent["password"]},
        )
        assert r.status_code == 303, r.text
        loc = r.headers.get("location") or ""
        assert f"{PREFIX}/portal" in loc, loc
        client.cookies.update(r.cookies)
        portal = client.get(f"{PREFIX}/portal", follow_redirects=True)
        assert portal.status_code == 200, portal.status_code
        body = portal.text.lower()
        assert agent["email"].split("@")[0] in body or agent["name"].split()[0].lower() in body
