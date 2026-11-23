"""Declared States-family pairs preserve all four stored components."""

from dataclasses import replace

import numpy as np
import pytest

from nmrglue import interop
from test_jcampdx_echo_antiecho import _fid


@pytest.mark.parametrize('quadrature,scheme', [('states', 'States'), ('states-tppi', 'States-TPPI')])
@pytest.mark.parametrize('conjugation', ['none', 'conjugate'])
def test_states_pairs_preserve_samples_and_caller_time(tmp_path, quadrature, scheme, conjugation):
    text, samples = _fid(6)
    path = tmp_path / 'states.dx'
    path.write_text(text.replace('Echo-Antiecho', scheme))
    source = interop.read(path, profile='jcampdx-fid-2d')
    result = interop.normalize(source, quadrature=quadrature, conjugation=conjugation,
                               confirm_adjacent_pairs=True, indirect_dwell_s=.003)
    if conjugation == 'conjugate':
        samples = samples.conj()
    np.testing.assert_array_equal(result.data, np.stack((samples[::2].real, samples[::2].imag,
                                                        samples[1::2].real, samples[1::2].imag)))
    np.testing.assert_array_equal(result.axes[0].values, [0, .003, .006])
    np.testing.assert_allclose(result.acquisition['spectral_width_hz'], [1/.003, 1000])
    assert result.branch_order == ('rr', 'ri', 'ir', 'ii')
    assert result.encoding == ('complex', 'complex')
    assert result.quadrature_mode == 'stored-components-2d'
    assert result.acquisition['indirect_sampling'] == quadrature
    assert result.acquisition.get('tppi_alternation') == (
        'declared_not_applied' if quadrature == 'states-tppi' else None)
    np.testing.assert_array_equal(source.data, _fid(6)[1])
    with pytest.raises(ValueError, match='description disagrees'):
        interop.normalize(replace(source, dimensions={}), quadrature=quadrature,
                          conjugation=conjugation, confirm_adjacent_pairs=True, indirect_dwell_s=.003)


@pytest.mark.parametrize('quadrature,scheme', [('states', 'States'), ('states-tppi', 'States-TPPI')])
@pytest.mark.parametrize('options', [
    {'confirm_adjacent_pairs': False}, {'confirm_adjacent_pairs': 1},
    {'indirect_dwell_s': None}, {'indirect_dwell_s': 0}, {'indirect_dwell_s': True},
    {'indirect_dwell_s': np.inf}, {'indirect_dwell_s': 1e-320}, {'conjugation': 'auto'},
])
def test_states_pair_options_are_explicit(tmp_path, quadrature, scheme, options):
    path = tmp_path / 'states.dx'
    path.write_text(_fid()[0].replace('Echo-Antiecho', scheme))
    source = interop.read(path, profile='jcampdx-fid-2d')
    kwargs = dict(quadrature=quadrature, conjugation='none', confirm_adjacent_pairs=True,
                  indirect_dwell_s=.003)
    with pytest.raises(ValueError):
        interop.normalize(source, **{**kwargs, **options})


@pytest.mark.parametrize('quadrature,scheme', [('states','States'),('states-tppi','States-TPPI')])
@pytest.mark.parametrize('rows,declared,direct', [
    (3, None, 'SIMULTANEOUS (DQD)'), (2, None, 'SIMULTANEOUS (DQD)'),
    (4, 'TPPI', 'SIMULTANEOUS (DQD)'), (4, 'Echo-Antiecho', 'SIMULTANEOUS (DQD)'),
    (4, None, 'SEQUENTIAL'),
])
def test_states_requires_matching_scheme_and_complete_dqd_pairs(tmp_path, quadrature, scheme, rows, declared, direct):
    path = tmp_path / 'bad.dx'
    path.write_text(_fid(rows)[0].replace('Echo-Antiecho', declared or scheme)
                    .replace('SIMULTANEOUS (DQD)', direct))
    source = interop.read(path, profile='jcampdx-fid-2d')
    with pytest.raises(ValueError):
        interop.normalize(source, quadrature=quadrature, conjugation='none',
                          confirm_adjacent_pairs=True, indirect_dwell_s=.003)
