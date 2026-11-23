"""Confirmed adjacent echo/anti-echo pairs with an explicit physical dwell."""

from dataclasses import replace

import numpy as np
import pytest

from nmrglue import interop


def _fid(rows=4):
    samples = np.arange(1, rows * 3 + 1).reshape(rows, 3)
    text = (
        '##TITLE=Synthetic echo/anti-echo\n##DATA TYPE=nD NMR FID\n'
        '##DATA CLASS=NTUPLES\n##NUM DIM=2\n'
        '##.ACQUISITION SCHEME=Echo-Antiecho\n'
        '##.ACQUISITION MODE=SIMULTANEOUS (DQD)\n'
        '##$GRPDLY=1.5\n##NTUPLES=nD NMR FID\n'
        '##SYMBOL=T1,T2,R,I\n'
        '##VAR_TYPE=INDEPENDENT,INDEPENDENT,DEPENDENT,DEPENDENT\n'
        f'##VAR_DIM={rows},3,3,3\n'
        '##UNITS=SECONDS,SECONDS,ARBITRARY UNITS,ARBITRARY UNITS\n'
        '##FACTOR=0.002,0.001,2,0.5\n##FIRST=0,0,2,5\n'
        f'##LAST={(rows - 1) * .002},0.002,{samples[-1, -1] * 2},{samples[-1, -1] * 5}\n'
    )
    for index, row in enumerate(samples):
        for component, values in [('R', row), ('I', 10 * row)]:
            text += f'##PAGE=T1={index * .002}\n##DATA TABLE=(T2++({component}..{component})), PROFILE\n'
            text += '0 ' + ' '.join(map(str, values)) + '\n'
    return text + '##END NTUPLES=nD NMR FID\n##END=\n', 2 * samples + 5j * samples


def _read(tmp_path, *, rows=4, substitutions=()):
    text, expected = _fid(rows)
    for old, new in substitutions:
        text = text.replace(old, new)
    path = tmp_path / 'echo.dx'
    path.write_text(text)
    return interop.read(path, profile='jcampdx-fid-2d'), expected


def _normalize(read, **options):
    return interop.normalize(read, **{
        'quadrature': 'echo-antiecho', 'conjugation': 'none',
        'confirm_adjacent_pairs': True, 'indirect_dwell_s': .003, **options,
    })


@pytest.mark.parametrize('conjugation', ['none', 'conjugate'])
def test_adjacent_pairs_and_physical_dwell_are_explicit(tmp_path, conjugation):
    read, expected = _read(tmp_path)
    result = _normalize(read, conjugation=conjugation)
    if conjugation == 'conjugate':
        expected = expected.conj()
    np.testing.assert_array_equal(result.data, np.stack((expected[::2], expected[1::2])))
    np.testing.assert_array_equal(result.axes[0].values, [0, .003])
    np.testing.assert_array_equal(result.axes[1].values, [0, .001, .002])
    np.testing.assert_allclose(result.acquisition['spectral_width_hz'], [1 / .003, 1000])
    assert result.branch_order == ('first', 'second')
    assert result.encoding == ('echo-antiecho', 'complex')
    assert result.quadrature_mode == 'echo-antiecho-stored-2d'
    assert result.acquisition['branch_order'] == 'stored'
    assert result.acquisition['reconstruction'] == 'not_applied'
    assert result.acquisition['indirect_dwell_source'] == 'caller'
    assert result.acquisition['digital_filter'] == {
        'applied': False, 'group_delay_points': 1.5, 'source': '$GRPDLY',
    }
    np.testing.assert_array_equal(read.data, _fid()[1])
    assert result.applied_operations[0]['conjugation'] == conjugation
    with pytest.raises(ValueError, match='description disagrees'):
        _normalize(replace(read, dimensions={'points': (2, 6)}))


@pytest.mark.parametrize('options', [
    {'confirm_adjacent_pairs': False}, {'confirm_adjacent_pairs': 1},
    {'indirect_dwell_s': None}, {'indirect_dwell_s': True},
    {'indirect_dwell_s': '0.003'}, {'indirect_dwell_s': 0},
    {'indirect_dwell_s': -1}, {'indirect_dwell_s': np.inf},
    {'indirect_dwell_s': np.nan}, {'indirect_dwell_s': 1e-320},
    {'conjugation': 'auto'},
])
def test_ambiguous_or_invalid_pair_options_are_rejected(tmp_path, options):
    read, _ = _read(tmp_path)
    with pytest.raises(ValueError):
        _normalize(read, **options)


@pytest.mark.parametrize('rows', [2, 3])
def test_requires_at_least_two_complete_pairs(tmp_path, rows):
    read, _ = _read(tmp_path, rows=rows)
    with pytest.raises(ValueError, match='complete.*pairs'):
        _normalize(read)


@pytest.mark.parametrize('old,new', [
    ('Echo-Antiecho', 'NOT PHASE SENSITIVE'),
    ('Echo-Antiecho', 'States-TPPI'),
    ('SIMULTANEOUS (DQD)', 'SEQUENTIAL'),
    ('##.ACQUISITION MODE=SIMULTANEOUS (DQD)\n', ''),
])
def test_requires_declared_echo_antiecho_with_direct_dqd(tmp_path, old, new):
    read, _ = _read(tmp_path, substitutions=[(old, new)])
    with pytest.raises(ValueError):
        _normalize(read)
