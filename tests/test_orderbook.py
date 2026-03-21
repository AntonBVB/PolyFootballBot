from polyfootballbot.orderbook import extract_book_top


def test_extract_book_top_uses_max_bid_and_min_ask() -> None:
    book = extract_book_top(
        {
            "bids": [{"price": 0.77, "size": 1}, {"price": 0.74, "size": 1}, {"price": 0.79, "size": 1}],
            "asks": [{"price": 0.83, "size": 1}, {"price": 0.82, "size": 1}, {"price": 0.84, "size": 1}],
        }
    )
    assert book.best_bid == 0.79
    assert book.best_ask == 0.82
    assert book.spread == 0.03
