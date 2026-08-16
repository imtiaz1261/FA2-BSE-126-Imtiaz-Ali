from app.pii import mask_pii
def test_pii():
 x=mask_pii("card 4111 1111 1111 1111 email a@example.com");assert "4111" not in x and "a@example.com" not in x
