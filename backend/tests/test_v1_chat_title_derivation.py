from app.v1.services.chat_service import ChatService


def test_derive_conversation_title_from_question():
    title = ChatService._derive_conversation_title("   show top 10 batters by total runs   ")
    assert title == "show top 10 batters by total runs"


def test_derive_conversation_title_truncates_long_question():
    long_question = "a" * 90
    title = ChatService._derive_conversation_title(long_question)
    assert len(title) == 60
    assert title.endswith("...")
