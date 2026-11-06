"""Explicit, bounded 1D nmrML normalization without vendor dispatch."""

from __future__ import annotations

from numbers import Real
import os
from urllib.parse import urlsplit

import numpy as np

from ..fileio import nmrml
from .result import Axis, Component, NormalizedAcquisition, ReadResult, Reference


def _positive(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(name + ' must be a positive finite scalar')
    value = float(value)
    if not np.isfinite(value) or value <= 0:
        raise ValueError(name + ' must be a positive finite scalar')
    return value


def _number(value, name):
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('nmrML requires numeric ' + name) from exc
    if not np.isfinite(result):
        raise ValueError('nmrML requires finite ' + name)
    return result


def _vocabulary(document, reference, family, description):
    entries = (document.get('cvList') or {}).get('cv') or []
    entries = entries if isinstance(entries, list) else [entries]
    matches = [entry for entry in entries if entry.get('@id') == reference]
    if len(matches) != 1:
        raise ValueError('nmrML ' + description + ' requires one declared CV reference')
    uri = urlsplit(matches[0].get('@URI', ''))
    path = uri.path.rstrip('/')
    if family == 'NMR':
        valid = uri.netloc.lower() == 'nmrml.org' and (path == '/cv' or path.startswith('/cv/'))
    else:
        generic_obo = path == '/obo' and matches[0].get('@fullName', '').strip().lower() == 'unit ontology'
        valid = (uri.netloc.lower() == 'purl.obolibrary.org' and (generic_obo or path == '/obo/uo.owl')) or (
            uri.netloc.lower() == 'unit-ontology.googlecode.com' and path == '/svn/trunk/uo.owl'
        )
    if uri.scheme not in ('http', 'https') or uri.query or uri.fragment or not valid:
        raise ValueError('nmrML ' + description + ' has an unknown CV vocabulary')


def _unit(document, value, allowed):
    aliases = {'hz': 'Hz', 'hertz': 'Hz', 'ppm': 'ppm', 'parts per million': 'ppm'}
    name = value.get('@unitName', '').strip().lower()
    unit = aliases.get(name)
    if unit not in allowed:
        raise ValueError('nmrML requires explicit compatible unit names')
    accession = value.get('@unitAccession')
    expected = {'Hz': 'UO:0000106', 'ppm': 'UO:0000169'}[unit]
    if accession is not None:
        for uri in ('http://purl.obolibrary.org/obo/', 'https://purl.obolibrary.org/obo/'):
            if accession.startswith(uri):
                accession = accession[len(uri):]
                break
        accession = accession.replace('UO_', 'UO:', 1)
        if accession != expected:
            raise ValueError('nmrML unit name and unit accession contradict each other')
    reference = value.get('@unitCvRef')
    if reference is not None:
        _vocabulary(document, reference, 'UO', 'unit')
    return unit


def _uniform_sampling(document, sampling):
    accession = sampling.get('@accession')
    if accession not in ('NMR:1000349', 'NMR_1000349', '1000349'):
        raise ValueError('nmrML time profile requires declared uniform sampling')
    name = sampling.get('@name', '').strip().lower()
    if name != 'uniform sampling':
        raise ValueError('nmrML sampling label contradicts its uniform accession')
    _vocabulary(document, sampling.get('@cvRef'), 'NMR', 'sampling')


def _describe(document, values, options, source):
    data = np.asarray(values)
    if (np.ma.is_masked(values) or data.ndim != 1 or data.size < 2
        or data.dtype.kind not in 'fc' or not np.isfinite(data).all()):
        raise ValueError('nmrML interop requires one finite unmasked 1D floating array')
    if document.get('@xmlns') != nmrml.NAMESPACE:
        raise ValueError('nmrML interop requires the schema namespace')
    processed = options['read_processed']
    selected, key = nmrml._select_array(document, processed, options['spectrum_index'])
    nmrml._check_count(selected, data, processed)
    decoded = nmrml._get_nmrml_data(selected[key], options['data_dtype'], strict=True)
    if decoded.dtype != data.dtype or not np.array_equal(decoded, data):
        raise ValueError('nmrML samples disagree with their encoded source')
    obs = options['observation_frequency_mhz']
    if obs is not None:
        obs = _positive(obs, 'observation_frequency_mhz')
    reference = Reference(observation_frequency=obs,
                          observation_frequency_unit='MHz' if obs is not None else None,
                          source='unknown')
    acquisition = {'normalization': 'none'}
    if obs is not None:
        acquisition['observation_frequency_mhz'] = obs
        acquisition['reference_evidence'] = 'explicit caller-supplied frequency, not inferred from acquisition'
    if processed:
        endpoint = options['axis_endpoint']
        if endpoint not in ('last-point', 'outer-edge'):
            raise ValueError('nmrML requires explicit axis_endpoint: last-point or outer-edge')
        xaxis = selected.get('xAxis') or {}
        unit = _unit(document, xaxis, ('Hz', 'ppm'))
        start = _number(xaxis.get('@startValue'), 'xAxis startValue')
        end = _number(xaxis.get('@endValue'), 'xAxis endValue')
        axis_values = np.linspace(start, end, data.size, endpoint=endpoint == 'last-point')
        if unit == 'ppm' and obs is not None:
            axis_values = axis_values * obs
            unit = 'Hz'
        domain = 'frequency'
        acquisition['axis_endpoint'] = endpoint
    else:
        if not np.iscomplexobj(data):
            raise ValueError('nmrML time profile requires complex samples')
        params = selected['acquisitionParameterSet']['DirectDimensionParameterSet']
        count_unit = options['raw_point_count']
        if count_unit not in ('complex', 'scalar'):
            raise ValueError('nmrML requires explicit raw_point_count: complex or scalar')
        expected = data.size * (2 if count_unit == 'scalar' else 1)
        if int(params['@numberOfDataPoints']) != expected:
            raise ValueError('nmrML raw point count disagrees with selected count convention')
        sampling = params.get('samplingStrategy') or {}
        _uniform_sampling(document, sampling)
        if params.get('samplingTimePoints') is not None:
            raise ValueError('nmrML explicit/nonuniform time grids are not qualified')
        sw = params.get('sweepWidth') or {}
        _unit(document, sw, ('Hz',))
        width = _positive(_number(sw.get('@value'), 'sweepWidth'), 'sweepWidth')
        axis_values = np.arange(data.size, dtype=float) / width
        unit, domain = 's', 'time'
        acquisition['spectral_width_hz'] = width
        acquisition['raw_point_count'] = count_unit
    differences = np.diff(axis_values)
    if (not np.isfinite(axis_values).all()
        or not (np.all(differences > 0) or np.all(differences < 0))):
        raise ValueError('nmrML axis must be finite and strictly monotonic')
    direction = 'increasing' if differences[0] > 0 else 'decreasing'
    mode = 'complex' if np.iscomplexobj(data) else 'real'
    return ReadResult(
        data=data, axes=(Axis(values=axis_values, unit=unit, domain=domain,
                             direction=direction, reference=reference),),
        components=(Component(name=mode, data=data),),
        metadata={'document': document, 'profile_options': options},
        applied_corrections={'normalization': 'none', 'conjugation': 'none'},
        format='nmrml-1d', source=source, domains=(domain,), encoding=(mode,),
        dimensions={'points': data.size}, acquisition=acquisition, diagnostics=(),
    )


def read_nmrml_1d(filename, *, read_processed=False, spectrum_index=None,
                  axis_endpoint=None, raw_point_count=None,
                  observation_frequency_mhz=None, data_dtype=None):
    """Describe one strictly decoded nmrML acquisition or processed spectrum.

    Processed xAxis requires an explicit endpoint convention: ``last-point``
    includes endValue; ``outer-edge`` excludes it. The XSD does not resolve this
    ambiguity. Hz/ppm units must be present. Acquisition frequency is never
    substituted for processing calibration: without an explicitly supplied MHz
    reference a ppm axis remains ppm, and cannot be converted to Hz here.
    Supplied MHz is recorded as caller evidence with unknown reference source,
    not certified as chemical calibration.

    Complex FIDs require ``raw_point_count='scalar'`` or ``'complex'``, declared
    uniform sampling and a positive Hz sweepWidth. Times are i/SW seconds.
    Sign, phase, gain, digital filtering and quadrature correction are not
    implicit. Supplied unit accessions/CV references and the complete uniform
    sampling term must be consistent; this is not whole-document CV validation. Unsupported/ambiguous metadata fail closed. No vendor inference,
    multidimensional data, nonuniform sampling or XY-pair layouts are qualified.
    """
    document, data = nmrml.read(filename, data_dtype=data_dtype, read_processed=read_processed,
                                 spectrum_index=spectrum_index, strict=True)
    options = {'read_processed': bool(read_processed), 'spectrum_index': spectrum_index,
               'axis_endpoint': axis_endpoint, 'raw_point_count': raw_point_count,
               'observation_frequency_mhz': observation_frequency_mhz,
               'data_dtype': None if data_dtype is None else np.dtype(data_dtype).str}
    return _describe(document, data, options, os.fspath(filename))


def normalize_nmrml_1d(result, *, conjugation=None):
    """Validate a 1D description and explicitly select raw complex sign policy.

    For FIDs ``conjugation`` must be ``'none'`` or ``'conjugate'``; this is a
    caller decision supported by external evidence, never selected by origin.
    Processed spectra accept only None/'none', preserving their samples.
    Source bytes/metadata and descriptive arrays are unchanged.
    """
    if not isinstance(result, ReadResult) or result.format != 'nmrml-1d':
        raise ValueError('normalize_nmrml_1d requires a nmrml-1d ReadResult')
    checked = _describe(result.metadata['document'], result.data,
                        result.metadata['profile_options'], result.source)
    if (result.domains != checked.domains or result.encoding != checked.encoding
        or len(result.axes) != 1 or len(result.components) != 1
        or result.components[0].name != checked.components[0].name
        or not np.array_equal(result.components[0].data, checked.data)
        or dict(result.applied_corrections) != dict(checked.applied_corrections)):
        raise ValueError('nmrML description disagrees with its source')
    axis, expected = result.axes[0], checked.axes[0]
    if (axis.unit != expected.unit or axis.domain != expected.domain
        or axis.direction != expected.direction or axis.reference != expected.reference
        or axis.values is None or not np.array_equal(axis.values, expected.values)):
        raise ValueError('nmrML axis disagrees with its source and explicit conventions')
    time_domain = checked.domains == ('time',)
    if (time_domain and conjugation not in ('none', 'conjugate')) or (
        not time_domain and conjugation not in (None, 'none')
    ):
        raise ValueError('nmrML FIDs require explicit conjugation; spectra are never conjugated')
    sign = conjugation or 'none'
    data = np.conjugate(checked.data) if sign == 'conjugate' else checked.data
    mode = checked.encoding[0]
    operation = {'name': 'normalize-nmrml-1d', 'stage': 'acquisition' if time_domain else 'processing',
                 'input_dimensions': ('storage',), 'output_dimensions': ('F2',),
                 'axis': 'F2', 'scale': None, 'conjugation': sign, 'sign': 'none',
                 'permutation': None, 'evidence': 'explicit nmrML 1D profile options'}
    return NormalizedAcquisition(
        data=data, axes=checked.axes, dimensions=('F2',), physical_dimensions=('F2',),
        domains=checked.domains, quadrature_mode=mode + '-1d', branch_order=(mode,),
        normalization_state='storage-normalized',
        normalization_profile='nmrml-' + ('time' if time_domain else 'spectrum') + '-1d-v1',
        applied_operations=(operation,), acquisition=checked.acquisition,
        provenance={'source': result.source, 'format': result.format},
        metadata=checked.metadata, encoding=checked.encoding, diagnostics=checked.diagnostics,
    )
