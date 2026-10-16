"""エージェントの作成・削除を管理するモジュール。"""

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

from config import PROJECT_ENDPOINT, MODEL_NAME, AGENT_NAME
from tools import TOOL_DEFINITIONS

SYSTEM_INSTRUCTIONS = """\
あなたはオンラインショップのカスタマーサポート担当のAIアシスタントです。
丁寧で親切な対応を心がけてください。

## 対応方針
- お客様の質問を正確に理解し、適切なツールを使って情報を取得してください。
- 注文状況の確認には lookup_order_status を使用してください。
- よくある質問への回答には search_faq を使用してください。
- お客様の問題を解決できない場合は create_support_ticket でチケットを作成してください。
- 製品に関する質問には get_product_info を使用してください。
- 最新情報や現在の状況について質問された場合は、web_search でインターネットを検索してください。
- MS Learn や Azure に関する質問では、Microsoft Learn などの公式情報を優先してください。
- Web検索で得た情報を回答に使う場合は、根拠となる情報源へのリンクを示してください。
- ツールで取得した情報をもとに、分かりやすく回答してください。
- 回答は日本語で行ってください。

## 注意事項
- 個人情報の取り扱いには十分注意してください。
- 不明な点がある場合は、お客様に確認してから対応してください。
- エスカレーションが必要な場合は、サポートチケットを作成してください。
"""


def create_project_client() -> AIProjectClient:
    """AIProjectClient を生成して返す。"""
    return AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )


def create_agent(project: AIProjectClient):
    """カスタマーサポートエージェントを作成して返す。"""
    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=MODEL_NAME,
            instructions=SYSTEM_INSTRUCTIONS,
            tools=TOOL_DEFINITIONS,
        ),
    )
    print(f"エージェントを作成しました: {agent.name} (version {agent.version})")
    return agent


def delete_agent(project: AIProjectClient, agent):
    """エージェントを削除する。"""
    project.agents.delete_version(
        agent_name=agent.name,
        agent_version=agent.version,
    )
    print(f"エージェントを削除しました: {agent.name} (version {agent.version})")
