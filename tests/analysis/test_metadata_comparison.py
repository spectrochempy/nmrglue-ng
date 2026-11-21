import numpy as np
import pytest

from nmrglue.util import misc


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('nested', [False, True])
def test_missing_scientific_metadata_is_not_similar(reverse, nested):
    left, right = {'obs': 400.}, {'obs': 400., 'sw': 800.}
    if nested:
        left, right = {'axis': left}, {'axis': right}
    if reverse:
        left, right = right, left
    assert misc.isdicsimilar(left, right) is False


@pytest.mark.parametrize('key', ['FDMIN', 'FDMAX', 'FDDISPMIN', 'FDDISPMAX', 'FDSCALEFLAG'])
@pytest.mark.parametrize('reverse', [False, True])
def test_missing_display_fields_are_ignored_only_when_requested(key, reverse):
    left, right = {'obs': 400.}, {'obs': 400., key: 123.}
    if reverse:
        left, right = right, left
    assert misc.isdicsimilar(left, right) is False
    assert misc.isdicsimilar(left, right, ignore_pipe_display=True) is True


def test_ignoring_display_does_not_hide_missing_scientific_keys():
    assert misc.isdicsimilar({'obs': 400.}, {'obs': 400., 'sw': 800.},
                            ignore_pipe_display=True) is False


def test_pair_comparison_propagates_key_mismatch_without_changing_data_result():
    data = np.arange(4, dtype=np.float32)
    assert misc.pair_similar({'obs': 400.}, data, {'obs': 400., 'sw': 800.}, data) == (True, False)


def test_existing_value_tolerances_are_preserved():
    assert misc.isdicsimilar({'value': 1.}, {'value': 1.4}) is True
    assert misc.isdicsimilar({'value': 1.}, {'value': 2.}) is False
