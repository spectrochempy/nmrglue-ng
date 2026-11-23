"""TopSpin per-page dependent dimensions and serialized physical PAGE values."""

from dataclasses import replace

import numpy as np
import pytest

from nmrglue import interop


SPECTRUM = """##TITLE=Per-page real 2D spectrum
##DATA TYPE=nD NMR SPECTRUM
##DATA CLASS=NTUPLES
##NUM DIM=2
##NTUPLES=nD NMR SPECTRUM
##SYMBOL=F1,F2,Y
##VAR_TYPE=INDEPENDENT,INDEPENDENT,DEPENDENT
##VAR_DIM=3,4,4
##UNITS=HZ,HZ,ARBITRARY UNITS
##FACTOR=2.5,2,-2
##FIRST=10.123456789,6,0
##LAST=5.123456789,0,0
##PAGE=F1=10.12345679
##DATA TABLE=(F2++(Y..Y)),PROFILE
3 1 2 3 4
##PAGE=F1=7.62345679
##DATA TABLE=(F2++(Y..Y)),PROFILE
3 5 6 7 8
##PAGE=F1=5.12345679
##DATA TABLE=(F2++(Y..Y)),PROFILE
3 9 10 11 12
##END NTUPLES=nD NMR SPECTRUM
##END=
"""


def test_topspin_per_page_profile_keeps_physical_axes_and_yfactor(tmp_path):
    path = tmp_path / 'processed.dx'
    path.write_text(SPECTRUM)
    read = interop.read(path, profile='jcampdx-spectrum-2d')
    result = interop.normalize(read)
    np.testing.assert_array_equal(result.data, -2*np.arange(1,13).reshape(3,4))
    np.testing.assert_array_equal(result.axes[0].values, [10.12345679,7.62345679,5.12345679])
    np.testing.assert_array_equal(result.axes[1].values, [6,4,2,0])
    assert result.domains == ('frequency','frequency')
    assert result.encoding == ('real','real')
    assert result.acquisition == {}
    with pytest.raises(ValueError,match='disagrees'):
        interop.normalize(replace(read, dimensions={}))


@pytest.mark.parametrize('old,new', [
    ('3,4,4','3,4,5'),
    ('FIRST=10.123456789,','FIRST=10,'), ('LAST=5.123456789,','LAST=5,'), ('FACTOR=2.5,2,-2','FACTOR=0,2,-2'),
    ('FACTOR=2.5,2,-2','FACTOR=2.5,0,-2'), ('FACTOR=2.5,2,-2','FACTOR=2.5,2,0'),
    ('PAGE=F1=10.12345679','PAGE=F1=10.12345680'),
    ('PAGE=F1=5.12345679','PAGE=F1=5.12345680'),
    ('PROFILE\n3 5','PROFILE\n8 5'), ('3 9 10 11 12','3 9 10 11'),
    ('##PAGE=F1=7.62345679\n',''),
])
def test_topspin_rejects_inconsistent_geometry_factors_and_pages(tmp_path,old,new):
    path = tmp_path / 'bad.dx'
    path.write_text(SPECTRUM.replace(old,new))
    with pytest.raises(ValueError):
        interop.read(path,profile='jcampdx-spectrum-2d')


def test_topspin_endpoint_rounding_includes_float_cancellation(tmp_path):
    count=1024
    first,last,step=19219.2484983975,-1593.73978285247,20.3450520833333
    text=(
        '##TITLE=Synthetic serialized grid\n##DATA TYPE=nD NMR SPECTRUM\n'
        '##DATA CLASS=NTUPLES\n##NUM DIM=2\n##NTUPLES=nD NMR SPECTRUM\n'
        f'##SYMBOL=F1,F2,Y\n##VAR_DIM={count},2,2\n'
        '##UNITS=HZ,HZ,ARBITRARY UNITS\n'
        f'##FIRST={first},1,1\n##LAST={last},0,2\n##FACTOR={step},1,1\n'
    )
    for index in range(count):
        coordinate=f'{first-index*step:.9f}' if index<count-1 else '-1593.739782853'
        text+=f'##PAGE=F1={coordinate}\n##DATA TABLE=(F2++(Y..Y)),PROFILE\n1 1 2\n'
    text+='##END NTUPLES=nD NMR SPECTRUM\n##END=\n'
    path=tmp_path/'rounded.dx';path.write_text(text)
    result=interop.read(path,profile='jcampdx-spectrum-2d')
    assert result.data.shape==(count,2)
    assert result.axes[0].values[-1]==-1593.739782853
    path.write_text(text.replace(f'##LAST={last},','##LAST=-1593.73978275,'))
    with pytest.raises(ValueError,match='PAGE endpoints'):
        interop.read(path,profile='jcampdx-spectrum-2d')
