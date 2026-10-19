from app import page


def test_page_returns_item() -> None:
    assert page(["first"], 0) == "first"
