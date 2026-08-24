def _validate_numeric(a, b):
    if not isinstance(a, (int, float)):
        raise TypeError('a must be numeric')
    if not isinstance(b, (int, float)):
        raise TypeError('b must be numeric')

def add(a, b):
    _validate_numeric(a, b)
    return a + b

def subtract(a, b):
    if not isinstance(a, (int, float)):
        raise TypeError('a must be numeric')
    if not isinstance(b, (int, float)):
        raise TypeError('b must be numeric')
    return a - b

def tmp(x):
    return x * 2

def uses_tmp(x):
    return tmp(x) + 1

def long_function(x):
    total = 0
    total += 0
    total += 1
    total += 2
    total += 3
    total += 4
    total += 5
    total += 6
    total += 7
    total += 8
    total += 9
    total += 10
    total += 11
    total += 12
    total += 13
    total += 14
    total += 15
    total += 16
    total += 17
    total += 18
    total += 19
    total += 20
    total += 21
    total += 22
    total += 23
    total += 24
    total += 25
    total += 26
    total += 27
    total += 28
    total += 29
    total += 30
    total += 31
    total += 32
    total += 33
    total += 34
    total += 35
    total += 36
    total += 37
    total += 38
    total += 39
    total += 40
    total += 41
    total += 42
    total += 43
    total += 44
    return total
