"""Convert the CC0 Bruker TopSpin Gossypol COSY fixture to NMRPipe."""

import argparse
from datetime import datetime
from pathlib import Path

import nmrglue as ng


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "output",
        type=Path,
        help="output NMRPipe .ft2 path (must not already exist)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="allow replacing the explicitly named output files",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and not args.overwrite:
        parser.error(f"output already exists: {output}")
    if not output.parent.is_dir():
        parser.error(f"output directory does not exist: {output.parent}")

    bruker_pdata = (
        Path(__file__).resolve().parent
        / "data/bruker_pdata/exp2d_cosy/pdata/1"
    )
    dic, data = ng.bruker.read_pdata(str(bruker_pdata))
    udic = ng.bruker.guess_udic(dic, data, pdata=True)
    for dim in range(udic["ndim"]):
        udic[dim].update(complex=False, time=False, freq=True)

    converter = ng.convert.converter()
    converter.from_bruker(dic, data, udic=udic)
    pipe_dic, pipe_data = converter.to_pipe(
        datetimeobj=datetime(2019, 8, 19, 17, 47, 22)
    )
    ng.pipe.write(str(output), pipe_dic, pipe_data, overwrite=args.overwrite)
    print(f"Wrote {output}: shape={pipe_data.shape}, dtype={pipe_data.dtype}")


if __name__ == "__main__":
    main()
