"""Configure an existing Dify App B draft for the T16 render-plan protocol."""

from __future__ import annotations

import argparse
import json

from app_factory import create_app
from extensions.ext_database import db
from models import Account, App
from services.workflow_service import WorkflowService
from sqlalchemy.orm import sessionmaker


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--prompt-file", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with open(args.prompt_file, encoding="utf-8-sig") as prompt_file:
        system_prompt = prompt_file.read()

    _, flask_app = create_app()
    with flask_app.app_context():
        with sessionmaker(db.engine).begin() as session:
            app = session.get(App, args.app_id)
            account = session.get(Account, args.account_id)
            if app is None or account is None:
                raise RuntimeError("App or account not found")

            service = WorkflowService()
            draft = service.get_draft_workflow(app_model=app, session=session)
            if draft is None:
                raise RuntimeError("Draft workflow not found")

            graph = json.loads(draft.graph)
            nodes = {node["id"]: node for node in graph["nodes"]}
            required_ids = {"start", "llm1", "answer1", "end1"}
            if set(nodes) != required_ids:
                raise RuntimeError(f"Unexpected App B node IDs: {sorted(nodes)}")

            start = nodes["start"]
            start["type"] = "custom"
            start["sourcePosition"] = "right"
            start["targetPosition"] = "left"
            start["data"]["variables"] = [
                {
                    "variable": variable,
                    "label": label,
                    "type": "paragraph",
                    "required": True,
                    "max_length": 100000,
                    "options": [],
                }
                for variable, label in (
                    ("script_plan", "ScriptPlan JSON 字符串"),
                    ("pause_profile", "停顿档案 JSON 字符串"),
                    ("voice_prompt", "用户声音描述"),
                    ("tts_context", "TTS 上下文 JSON 字符串"),
                )
            ]

            llm = nodes["llm1"]
            llm["type"] = "custom"
            llm["sourcePosition"] = "right"
            llm["targetPosition"] = "left"
            llm["data"]["title"] = "生成音频编排计划"
            llm["data"]["model"]["name"] = "deepseek-v4-flash"
            llm["data"]["reasoning_format"] = "separated"
            llm["data"]["prompt_template"] = [{"role": "system", "text": system_prompt}]
            llm["data"]["variables"] = [
                {
                    "variable_selector": ["start", variable],
                    "value_selector": ["start", variable],
                }
                for variable in ("script_plan", "pause_profile", "voice_prompt", "tts_context")
            ]

            answer = nodes["answer1"]
            answer["type"] = "custom"
            answer["sourcePosition"] = "right"
            answer["targetPosition"] = "left"
            answer["data"]["title"] = "直接回复"
            answer["data"]["answer"] = "{{#llm1.text#}}"

            end = nodes["end1"]
            end["type"] = "custom"
            end["sourcePosition"] = "right"
            end["targetPosition"] = "left"
            end["data"]["outputs"] = [
                {"variable": "result", "value_selector": ["llm1", "text"]}
            ]

            expected_edges = {
                ("start", "llm1"),
                ("llm1", "answer1"),
                ("answer1", "end1"),
            }
            actual_edges = {(edge["source"], edge["target"]) for edge in graph["edges"]}
            if actual_edges != expected_edges:
                raise RuntimeError(f"Unexpected App B edges: {sorted(actual_edges)}")
            for edge in graph["edges"]:
                edge["sourceHandle"] = "source"
                edge["targetHandle"] = "target"
                edge["type"] = "custom"
                edge.setdefault("data", {})
                edge["data"].update(
                    {
                        "sourceType": nodes[edge["source"]]["data"]["type"],
                        "targetType": nodes[edge["target"]]["data"]["type"],
                        "isInIteration": False,
                        "isInLoop": False,
                    }
                )

            updated = service.sync_draft_workflow(
                app_model=app,
                graph=graph,
                features=draft.features_dict,
                unique_hash=draft.unique_hash,
                account=account,
                environment_variables=draft.environment_variables,
                conversation_variables=draft.conversation_variables,
                session=session,
                commit=False,
            )
            print(json.dumps({"workflow_id": updated.id, "hash": updated.unique_hash}))


if __name__ == "__main__":
    main()
