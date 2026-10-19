from app.services.conversation_service import ConversationService


def test_conversation_round_trip(aws_mock):
    conv = ConversationService()
    conversation_id = conv.create_conversation("user1")

    conv.append_turn(conversation_id, "user", "What is the refund window?")
    conv.append_turn(conversation_id, "assistant", "14 days from purchase.")

    turns = conv.get_recent_turns(conversation_id, limit=6)
    assert turns == [
        {"role": "user", "content": "What is the refund window?"},
        {"role": "assistant", "content": "14 days from purchase."},
    ]


def test_get_recent_turns_limits_history(aws_mock):
    conv = ConversationService()
    conversation_id = conv.create_conversation("user1")
    for i in range(10):
        conv.append_turn(conversation_id, "user", f"question {i}")

    turns = conv.get_recent_turns(conversation_id, limit=4)
    assert len(turns) == 4
    assert turns[-1]["content"] == "question 9"


def test_unknown_conversation_returns_empty_history(aws_mock):
    conv = ConversationService()
    conv.ensure_table_exists()
    assert conv.get_recent_turns("does-not-exist", limit=6) == []
