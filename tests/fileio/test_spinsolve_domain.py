import struct

import numpy as np
import pytest

from nmrglue.fileio import spinsolve


def write_binary_experiment(path, filename):
    (path / 'acqu.par').write_text(
        'bandwidth=5\nb1Freq=43.5\nlowestFrequency=-2500\nrxChannel="1H"\n')
    header = struct.pack('<8I', 0, 0, 0, 0, 4, 1, 1, 1)
    axis = np.array([10., 9., 8., 7.], dtype='<f4')
    values = np.array([1., .25, 2., .5, 3., .75, 4., 1.], dtype='<f4')
    (path / filename).write_bytes(header + axis.tobytes() + values.tobytes())


@pytest.mark.parametrize('filename, frequency', [
    ('data.1d', False), ('fid.1d', False),
    ('spectrum.1d', True), ('spectrum_processed.1d', True),
])
@pytest.mark.parametrize('explicit', [False, True])
def test_known_binary_file_domain(tmp_path, filename, frequency, explicit):
    write_binary_experiment(tmp_path, filename)
    dic, data = spinsolve.read(tmp_path, specfile=filename if explicit else None)
    udic = spinsolve.guess_udic(dic, data)
    assert udic[0]['freq'] is frequency
    assert udic[0]['time'] is not frequency
    np.testing.assert_array_equal(data, [1.+.25j, 2.+.5j, 3.+.75j, 4.+1j])
    np.testing.assert_array_equal(dic['spectrum']['xaxis'], [10., 9., 8., 7.])
    assert udic[0]['sw'] == 5000.
    assert udic[0]['obs'] == 43.5


def test_domain_uses_selected_file_not_other_files_in_directory(tmp_path):
    write_binary_experiment(tmp_path, 'data.1d')
    write_binary_experiment(tmp_path, 'spectrum.1d')
    dic, data = spinsolve.read(tmp_path)
    assert spinsolve.guess_udic(dic, data)[0]['time'] is True
    dic, data = spinsolve.read(tmp_path, specfile='spectrum.1d')
    assert spinsolve.guess_udic(dic, data)[0]['freq'] is True


def test_legacy_dictionary_without_source_keeps_default_domain():
    dic = {'acqu': {'bandwidth':5, 'b1Freq':43.5, 'lowestFrequency':-2500,
                    'rxChannel':'1H'}, 'dx':{}, 'spectrum':{}}
    axis = spinsolve.guess_udic(dic, np.ones(4))[0]
    assert axis['time'] is True
    assert axis['freq'] is False
