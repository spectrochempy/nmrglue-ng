# Convert experimental data between formats

The {doc}`conversion lesson <../tutorials/converting-formats>` explains the
shared converter. For every format pair, read the array and metadata, verify
the axis description, write the target, and read it back. The examples below
change the input and the quadrature, so the shared workflow only needs to
be learned once.

## Start with a 1D FID

Run the Agilent example first. Its notebook supplies a known sweep width,
observation frequency and carrier for that dataset. Those are acquisition
values, so use your own metadata for a different experiment. Repeat with
Bruker and compare how the two readers describe the direct axis before
writing the same target format.

Once the Agilent notebook has read the FID and filled in its acquisition
metadata, the conversion itself is only three steps:

```python
converter = ng.convert.converter()
converter.from_varian(varian_dic, varian_data, udic)
pipe_dic, pipe_data = converter.to_pipe()
```

The notebook then writes and reads back the output. Compare the returned
array with `pipe_data` before using the file in the processing chapter.

```{toctree}
:maxdepth: 1

../examples/agilent2pipe_1d
../examples/bruker2pipe_1d
```

## Extend the conversion to indirect dimensions

In 2D, check which axis is indirect and how its quadrature is stored. Use
the regular Agilent example as a baseline, then compare its TPPI counterpart
and the Bruker conversion. The 3D examples apply the same idea to another
axis and show why {doc}`low-memory access <../tutorials/low-memory>` matters.

```{toctree}
:maxdepth: 1

../examples/agilent2pipe_2d
../examples/agilent2pipe_2d_tppi
../examples/bruker2pipe_2d
../examples/agilent2pipe_3d
../examples/bruker2pipe_3d
```

## Exchange processed spectra with Sparky

Convert an already processed NMRPipe spectrum to Sparky and check that its
dimensions and ppm axes still describe the same experiment. Then reverse
the direction with the experimental S1 listing. Its verified result
shows that all samples survive conversion and re-reading.

```{toctree}
:maxdepth: 1

../examples/pipe2sparky_2d
../examples/pipe2sparky_3d
../jbnmr_examples/s1_sparky_to_nmrpipe
```

## Exchange 1D spectra as nmrML

For a 1D exchange file with XML metadata, use the nmrML workflow. Check the
round trip with the same sample and metadata checks as for binary formats.

```{toctree}
:maxdepth: 1

Reading and writing nmrML 1D </nmrml_1d>
```
