from chatbot.parser import parse_locally

def test_english_and_hinglish_requests():
    assert parse_locally("Convert 10 kilograms to pounds").from_unit == "kilogram"
    request = parse_locally("5 km ko miles mein convert karo")
    assert (request.value, request.from_unit, request.to_unit) == (5.0, "kilometer", "mile")
