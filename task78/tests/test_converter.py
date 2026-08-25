import pytest
from conversion.converter import ConversionError, convert_unit

def test_length_and_aliases():
    assert convert_unit(5, "km", "miles") == pytest.approx(3.106856, rel=1e-6)
    assert convert_unit(1, "feet", "cm") == pytest.approx(30.48)

def test_weight_and_volume():
    assert convert_unit(10, "kg", "lbs") == pytest.approx(22.0462262)
    assert convert_unit(2500, "ml", "l") == pytest.approx(2.5)

def test_temperature_and_negative_values():
    assert convert_unit(25, "celsius", "fahrenheit") == pytest.approx(77)
    assert convert_unit(-40, "C", "F") == pytest.approx(-40)
    assert convert_unit(0, "celsius", "kelvin") == pytest.approx(273.15)

def test_errors():
    with pytest.raises(ConversionError): convert_unit(1, "banana", "meter")
    with pytest.raises(ConversionError): convert_unit(1, "kg", "meter")
