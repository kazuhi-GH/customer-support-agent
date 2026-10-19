"""カスタマーサポートエージェント用 Function Tool 定義と実装。

各関数はデモ用のモックデータを返します。
実運用では、データベースや外部APIへの接続に置き換えてください。
"""

import json
from azure.ai.projects.models import FunctionTool, MCPTool, Tool, WebSearchTool

# ---------------------------------------------------------------------------
# モック データ（実運用ではDB/APIに置き換え）
# ---------------------------------------------------------------------------

_ORDERS = {
    "ORD-1001": {"status": "配送中", "item": "ワイヤレスヘッドフォン", "eta": "2025-07-20"},
    "ORD-1002": {"status": "準備中", "item": "USBハブ 7ポート", "eta": "2025-07-22"},
    "ORD-1003": {"status": "配達完了", "item": "モニタースタンド", "delivered": "2025-07-10"},
}

_FAQS = [
    {"q": "返品ポリシー", "a": "商品到着後30日以内であれば、未使用・未開封の場合に限り返品が可能です。返品送料はお客様負担となります。"},
    {"q": "配送日数", "a": "通常配送は3〜5営業日、お急ぎ便は1〜2営業日でお届けします。"},
    {"q": "支払い方法", "a": "クレジットカード（Visa/Mastercard/JCB）、デビットカード、コンビニ決済、銀行振込に対応しています。"},
    {"q": "注文キャンセル", "a": "発送準備前であればキャンセルが可能です。マイページの注文履歴からキャンセルしてください。"},
    {"q": "保証期間", "a": "すべての製品に1年間のメーカー保証が付きます。延長保証プランもご利用いただけます。"},
]

_PRODUCTS = {
    "PROD-001": {"name": "ワイヤレスヘッドフォン", "price": 12800, "stock": True},
    "PROD-002": {"name": "USBハブ 7ポート", "price": 3980, "stock": True},
    "PROD-003": {"name": "モニタースタンド", "price": 6500, "stock": False},
}

_TICKET_COUNTER = 0


# ---------------------------------------------------------------------------
# Function Tool 実装
# ---------------------------------------------------------------------------

def lookup_order_status(order_id: str) -> str:
    """注文番号から注文のステータスを検索して返す。"""
    order = _ORDERS.get(order_id.upper())
    if order is None:
        return json.dumps({"error": f"注文番号 {order_id} が見つかりません。"}, ensure_ascii=False)
    return json.dumps({"order_id": order_id.upper(), **order}, ensure_ascii=False)


def search_faq(query: str) -> str:
    """キーワードで FAQ を検索し、関連するQ&Aを返す。"""
    query_lower = query.lower()
    results = [
        faq for faq in _FAQS
        if query_lower in faq["q"].lower() or query_lower in faq["a"].lower()
    ]
    if not results:
        return json.dumps({"message": "該当するFAQが見つかりませんでした。"}, ensure_ascii=False)
    return json.dumps(results, ensure_ascii=False)


def create_support_ticket(subject: str, description: str, priority: str = "normal") -> str:
    """サポートチケットを作成する。"""
    global _TICKET_COUNTER
    _TICKET_COUNTER += 1
    ticket_id = f"TKT-{_TICKET_COUNTER:04d}"
    return json.dumps({
        "ticket_id": ticket_id,
        "subject": subject,
        "description": description,
        "priority": priority,
        "status": "受付済み",
    }, ensure_ascii=False)


def get_product_info(product_id: str) -> str:
    """製品IDから製品情報を取得する。"""
    product = _PRODUCTS.get(product_id.upper())
    if product is None:
        return json.dumps({"error": f"製品ID {product_id} が見つかりません。"}, ensure_ascii=False)
    return json.dumps({"product_id": product_id.upper(), **product}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 定義（エージェント登録用）
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[Tool] = [
    FunctionTool(
        name="lookup_order_status",
        description="注文番号から注文の現在のステータス・配送予定日を検索します。",
        parameters={
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "注文番号（例: ORD-1001）",
                },
            },
            "required": ["order_id"],
            "additionalProperties": False,
        },
        strict=True,
    ),
    FunctionTool(
        name="search_faq",
        description="キーワードでFAQ（よくある質問）を検索し、関連する回答を返します。",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索キーワード（例: 返品、配送、支払い）",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        strict=True,
    ),
    FunctionTool(
        name="create_support_ticket",
        description="お客様の問題についてサポートチケットを新規作成します。",
        parameters={
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "チケットの件名",
                },
                "description": {
                    "type": "string",
                    "description": "問題の詳細な説明",
                },
                "priority": {
                    "type": "string",
                    "description": "優先度",
                    "enum": ["low", "normal", "high", "urgent"],
                },
            },
            "required": ["subject", "description", "priority"],
            "additionalProperties": False,
        },
        strict=True,
    ),
    FunctionTool(
        name="get_product_info",
        description="製品IDから製品の名前・価格・在庫状況を取得します。",
        parameters={
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "製品ID（例: PROD-001）",
                },
            },
            "required": ["product_id"],
            "additionalProperties": False,
        },
        strict=True,
    ),
    MCPTool(
        server_label="microsoft_learn",
        server_url="https://learn.microsoft.com/api/mcp",
        require_approval="never",
    ),
    WebSearchTool(external_web_access=True, search_context_size="high"),
]

# 関数名 → 実装のマッピング
TOOL_FUNCTIONS: dict[str, callable] = {
    "lookup_order_status": lookup_order_status,
    "search_faq": search_faq,
    "create_support_ticket": create_support_ticket,
    "get_product_info": get_product_info,
}
