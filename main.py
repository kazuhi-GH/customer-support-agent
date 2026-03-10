"""カスタマーサポートエージェント — メインエントリポイント。

Foundry Agent Service (New API) を使用したマルチターン会話ループ。
ストリーミングレスポンスおよび Function Calling に対応。

使い方:
  1. .env ファイルに PROJECT_ENDPOINT を設定
  2. az login でサインイン
  3. pip install -r requirements.txt
  4. python main.py
"""

import json
import sys

from openai.types.responses.response_input_param import (
    FunctionCallOutput,
    ResponseInputParam,
)

from agent import create_project_client, create_agent, delete_agent
from tools import TOOL_FUNCTIONS


def handle_function_calls(response) -> list[FunctionCallOutput]:
    """レスポンスに含まれる Function Call を実行し、結果のリストを返す。"""
    outputs: list[FunctionCallOutput] = []
    for item in response.output:
        if item.type != "function_call":
            continue
        func = TOOL_FUNCTIONS.get(item.name)
        if func is None:
            result = json.dumps({"error": f"Unknown function: {item.name}"})
        else:
            args = json.loads(item.arguments)
            result = func(**args)
        outputs.append(
            FunctionCallOutput(
                type="function_call_output",
                call_id=item.call_id,
                output=result,
            )
        )
    return outputs


def run_turn(openai_client, agent_name: str, user_input: str, previous_response_id: str | None = None):
    """1ターンの会話を実行し、(最終テキスト応答, response_id) を返す。

    Function Call が発生した場合は、関数を実行して結果を送り返す
    ループを最終応答が得られるまで繰り返す。
    """
    # レスポンスを生成
    kwargs: dict = {
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": user_input}]}],
        "extra_body": {
            "agent_reference": {"name": agent_name, "type": "agent_reference"},
        },
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    response = openai_client.responses.create(**kwargs)

    # Function Call がある限りループ
    while True:
        tool_outputs = handle_function_calls(response)
        if not tool_outputs:
            break

        # Function Call 結果を送信して次のレスポンスを取得
        input_list: ResponseInputParam = tool_outputs
        response = openai_client.responses.create(
            input=input_list,
            previous_response_id=response.id,
            extra_body={
                "agent_reference": {"name": agent_name, "type": "agent_reference"},
            },
        )

    return response.output_text, response.id


def main():
    project = create_project_client()
    openai = project.get_openai_client()
    agent = create_agent(project)

    # 会話を開始
    print("=" * 60)
    print("カスタマーサポートへようこそ！ご質問をどうぞ。")
    print("終了するには 'quit' または 'exit' と入力してください。")
    print("=" * 60)

    previous_response_id = None
    try:
        while True:
            try:
                user_input = input("\nお客様 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break

            reply, previous_response_id = run_turn(openai, agent.name, user_input, previous_response_id)
            print(f"\nサポート > {reply}")

    finally:
        # クリーンアップ
        print("\n--- クリーンアップ中 ---")
        delete_agent(project, agent)
        print("お問い合わせありがとうございました。")


if __name__ == "__main__":
    main()
