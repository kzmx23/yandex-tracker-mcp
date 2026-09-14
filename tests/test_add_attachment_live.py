"""Живой end-to-end тест нового инструмента вложений форка.

Прикрепляет временный файл к задаче через TrackerClient.issue_add_attachment,
проверяет ответ и удаляет тестовое вложение через тот же aiohttp-сеанс, чтобы
не оставлять мусор в задаче.

Запуск (из корня форка, деды резолвит uv):
    uv run --directory . python tests/test_add_attachment_live.py

Креды берутся из ~/.claude.json (mcpServers.yandex-tracker.env). Ключ задачи
передаётся первым аргументом (по умолчанию QUEUE-1 — замените на свой).
"""
import asyncio
import json
import os
import sys
import tempfile

from mcp_tracker.tracker.custom.client import TrackerClient


async def main() -> int:
    issue_id = sys.argv[1] if len(sys.argv) > 1 else "QUEUE-1"
    cfg = json.load(open(os.path.expanduser("~/.claude.json"), encoding="utf-8"))
    env = cfg["mcpServers"]["yandex-tracker"]["env"]
    token, org = env["TRACKER_TOKEN"], str(env["TRACKER_ORG_ID"])

    client = TrackerClient(token=token, token_type="OAuth", org_id=org)
    await client.prepare()
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tf:
            tf.write("mcp attachment self-test — можно удалять\n")
            path = tf.name

        att = await client.issue_add_attachment(
            issue_id, file_path=path, filename="mcp_test.txt"
        )
        assert att.id, "нет id у вложения"
        assert att.name == "mcp_test.txt", f"имя не совпало: {att.name}"
        print(f"ATTACH OK id={att.id} name={att.name} size={att.size}")

        # уборка: удалить тестовое вложение тем же сеансом
        headers = await client._build_headers(None)
        async with client._session.delete(
            f"v3/issues/{issue_id}/attachments/{att.id}", headers=headers
        ) as r:
            print(f"DELETE status={r.status}")
            assert r.status in (200, 204), f"удаление не удалось: {r.status}"
        os.unlink(path)
        print("SELFTEST_OK")
        return 0
    finally:
        await client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
