from calc import add, subtract, tmp, uses_tmp, long_function

def test_add():
    assert add(2, 3) == 5

def test_subtract():
    assert subtract(5, 2) == 3

def test_uses_tmp():
    assert uses_tmp(4) == 9

def test_long_function():
    assert long_function(0) == sum(range(45))
