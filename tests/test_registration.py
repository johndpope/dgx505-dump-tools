import pytest
import json

from commons.mido_util import read_syx_file
from commons.dumpdata.regdata import RegDumpSection


@pytest.mark.parametrize("datafile, valuefile", [
    ('test_data/regtest1.txt', 'test_data/regtest1.json'),
    ('test_data/regtest2.txt', 'test_data/regtest2.json'),
    ('test_data/regtest3.syx', 'test_data/regtest3.json')
])
def test_reg(datafile, valuefile):
    with open(datafile, 'rb') as infile:
        msgs = read_syx_file(infile)
        dobj = RegDumpSection(msgs, verbose=True).settings
    with open(valuefile, 'r') as vfile:
        sets = json.load(vfile)
    dset = dobj.get_setting(4, 2)
    assert len(dset._unusual) == 0
    for key, value in sets.items():
        assert dset[key].value == value
