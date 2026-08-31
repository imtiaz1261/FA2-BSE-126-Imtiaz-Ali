import pytest
from strength_checker import check_password_strength

def test_strong(): assert check_password_strength('Abcd1234!')['label']=='Strong'
def test_missing_uppercase(): assert not check_password_strength('abcd1234!')['checks']['uppercase']
def test_missing_number(): assert not check_password_strength('Abcdefgh!')['checks']['number']
def test_missing_symbol(): assert not check_password_strength('Abcd12345')['checks']['symbol']
def test_short(): assert not check_password_strength('A1!')['checks']['length']
def test_long_bonus(): assert check_password_strength('Abcd1234!LongPass')['score']>=check_password_strength('Abcd1234!')['score']
def test_empty(): assert check_password_strength('')['score']==0
def test_type():
    with pytest.raises(TypeError): check_password_strength(None)
