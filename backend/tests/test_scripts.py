async def _create_script(client, title="测试引导词", content="请闭上眼睛..."):
    resp = await client.post("/api/scripts", json={"title": title, "content": content})
    assert resp.status_code == 201
    return resp.json()


async def test_create_script(client):
    data = await _create_script(client)
    assert data["id"] is not None
    assert data["title"] == "测试引导词"
    assert data["pause_capable"] is False


async def test_create_structured_script_generates_content_and_ids(client):
    resp = await client.post(
        "/api/scripts",
        json={
            "title": "结构化脚本",
            "script_plan": {
                "version": 1,
                "target_duration_seconds": 600,
                "blocks": [
                    {"text": "第一段。", "pause_after": {"kind": "paragraph"}},
                    {"text": "第二段。", "pause_after": {"kind": "ending"}},
                ],
            },
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["content"] == "第一段。\n\n第二段。"
    assert [block["id"] for block in body["script_plan"]["blocks"]] == ["b1", "b2"]
    assert body["pause_capable"] is True
    assert body["target_duration_seconds"] == 600


async def test_structured_script_rejects_conflicting_content(client):
    resp = await client.post(
        "/api/scripts",
        json={
            "title": "漂移",
            "content": "另一份正文",
            "script_plan": {
                "version": 1,
                "target_duration_seconds": 60,
                "blocks": [{"text": "真实正文", "pause_after": {"kind": "short"}}],
            },
        },
    )
    assert resp.status_code == 422


async def test_list_scripts_empty(client):
    resp = await client.get("/api/scripts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_list_scripts_pagination(client):
    for i in range(5):
        await _create_script(client, title=f"引导词{i}")

    resp = await client.get("/api/scripts?page=1&page_size=2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2

    resp = await client.get("/api/scripts?page=3&page_size=2")
    body = resp.json()
    assert len(body["items"]) == 1


async def test_get_script(client):
    created = await _create_script(client)
    resp = await client.get(f"/api/scripts/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["content"] == "请闭上眼睛..."


async def test_get_script_404(client):
    resp = await client.get("/api/scripts/999")
    assert resp.status_code == 404


async def test_update_script(client):
    created = await _create_script(client)
    resp = await client.put(
        f"/api/scripts/{created['id']}",
        json={"title": "更新标题", "content": "更新内容"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "更新标题"


async def test_delete_script(client):
    created = await _create_script(client)
    resp = await client.delete(f"/api/scripts/{created['id']}")
    assert resp.status_code == 204
    resp = await client.get(f"/api/scripts/{created['id']}")
    assert resp.status_code == 404
