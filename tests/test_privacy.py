from app.privacy import anonymized_id

def test_anonymization_is_stable_and_not_plaintext():
    a=anonymized_id('user@example.com'); b=anonymized_id('user@example.com'); assert a==b; assert a!='user@example.com'; assert len(a)==16
