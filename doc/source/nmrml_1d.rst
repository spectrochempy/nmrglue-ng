nmrML 1D: binary round trips and explicit interop
=================================================

nmrML is an exchange format, not the native Varian/Agilent processed format.
The reader and writer preserve stored samples and metadata; they do not
reprocess, phase, rescale or chemically recalibrate spectra.

Low-level read and write
------------------------

Install optional ``xmltodict`` to use the XML reader/writer. The historical
``read(filename, data_dtype=None, read_processed=False)`` return contract is
unchanged. Select one spectrum explicitly if a document contains several::

    import nmrglue as ng

    metadata, data = ng.nmrml.read(
        "source.nmrML", read_processed=True, spectrum_index=0, strict=True
    )
    ng.nmrml.write(
        "copy.nmrML", metadata, data, write_processed=True,
        spectrum_index=0, compressed=True
    )

``write`` copies metadata and replaces only the selected array. Float32/64 and
complex64/128 precision are preserved; bytes are always little-endian. Counts
must already match: changing data length requires explicit coherent metadata.
Other spectra/annotations remain present. Existing outputs require
``overwrite=True``. No metadata generator or axis recalibration is provided.

The legacy encoded-length warning is retained by default; strict reading
rejects mismatches and incoherent point counts. XML boolean values 0/1 and
true/false, namespace prefixes and whitespace in base64 are supported.
Malformed base64, incomplete scalar samples and corrupt/trailing zlib streams
are rejected. ``data_dtype`` remains an explicit escape hatch for incorrectly
labelled legacy arrays, never an automatic guess.

Schema validation is optional: pass ``schema="local/nmrML.xsd"`` to ``write``
with optional ``lxml`` installed. Validation completes before output is opened.
No schema or spectrum is downloaded implicitly. The pinned official schema in
the tests is MIT licensed and declares version 1.0.rc1. Passing XSD validation
checks XML structure, not CV meaning, calibration, binary interpretation or
scientific fidelity. Invalid legacy metadata are preserved, not silently repaired.

Scientific normalization
------------------------

The neutral bridge is explicit; there is no automatic reader-dispatch switch::

    raw = ng.interop.read_nmrml_1d(
        "source.nmrML", read_processed=True, axis_endpoint="last-point"
    )
    normalized = ng.interop.normalize_nmrml_1d(raw)

Processed axes must declare Hz or ppm. The schema does not distinguish whether
endValue is the last sample or the outer edge of a half-open grid. Choose
``axis_endpoint="last-point"`` (N-1 intervals) or ``"outer-edge"`` (N intervals)
from independent knowledge of the producer. No choice is inferred from vendor
origin or a discrepancy with the acquisition sweep width.

Without an explicitly supplied ``observation_frequency_mhz``, a ppm axis stays
ppm. Acquisition excitation frequency is never substituted for the processing
reference. An explicitly supplied MHz reference permits Hz/ppm conversion and
is recorded as caller evidence with reference source ``unknown``; chemical
referencing is not certified by this conversion.

For complex uniformly sampled FIDs::

    raw = ng.interop.read_nmrml_1d(
        "source.nmrML", raw_point_count="scalar", data_dtype="<c8"
    )
    normalized = ng.interop.normalize_nmrml_1d(raw, conjugation="none")

Choose ``raw_point_count="complex"`` or ``"scalar"`` explicitly. Time is i/SW
seconds only for declared uniform sampling and positive Hz spectral width.
``conjugation="none"`` or ``"conjugate"`` is required; its selection needs
producer/reference evidence. No gain, digital-filter, phase or receiver
correction is implicit. A dtype override likewise needs independent evidence.
The normalizer revalidates binary samples and axes before constructing its
immutable result. Origin remains opaque provenance.

Qualified evidence and limits
-----------------------------

Synthetic tests cover real/complex precision, byte order, compression,
namespace prefixes, multi-spectrum selection, malformed input, XSD validation,
explicit grid conventions, normalized immutability and caller ownership.

Two public official examples are external local qualification inputs, not
redistributed fixtures. The hop FID is mislabelled Complex128: an explicit
``<c8`` override yields 32768 complex samples exactly equal to the native
Varian FID. Its excitation metadata also disagree with the native procpar;
the bridge does not use them as an observation reference. The Bayesil example
stores 32768 complex spectral samples; its unrelated FID encodedLength is
incorrect. Selected spectral decoding is independently checked using XML,
base64 and binary words. Endpoint interpretation is conditional on the explicit
caller convention, not independently certified by that file alone. Both public
legacy XML documents fail the pinned XSD; their round trips are not presented
as schema-valid conversions.

No multidimensional data, nonuniform sampling, XY-pair layouts, universal native
processed conversion, implicit reference or correction is qualified. Missing,
non-finite, inconsistent or ambiguous metadata fail closed in the bridge.
Element names are resolved by namespace URI, so aliases are accepted without
interpreting foreign elements as nmrML. Supplied unit accessions must match
Hz/ppm names, and referenced CVs must identify the supported vocabularies.
Uniform sampling requires the complete NMR term and a consistent label.
These checks cover metadata used by the profile, not the entire document CV.
Native processed Varian support and chemical reference qualification remain
separate tasks. A portable upstream candidate is the low-level reader/writer;
the normalized bridge depends on nmrglue-ng's additive interop contract.
