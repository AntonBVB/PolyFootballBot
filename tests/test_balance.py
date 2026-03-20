from polyfootballbot.clob import parse_available_balance


def test_parse_available_balance_formats() -> None:
    assert parse_available_balance({"available": 12.5}) == 12.5
    assert parse_available_balance({"balance": 7}) == 7.0
    assert parse_available_balance({"data": {"available": 11}}) == 11.0
    assert parse_available_balance({"data": {"balance": 2_500_000}}) == 2.5
