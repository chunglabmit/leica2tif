import argparse
import itertools
import os

import bioformats
import javabridge
import sys
import tifffile
import tqdm

def parse_args(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",
                        help=".lif file to be read",
                        required=True)
    parser.add_argument("--output-pattern",
                        help="Output pattern for files, with format escapes "
                             "for z, t and c, e.g. "
                             "\"/path-to/img_z{z:04d}_c{c01d}_t{t04d}.tiff",
                        required=True)
    parser.add_argument("--z-min",
                        help="Minimum z frame to process. Default is all.",
                        type=int)
    parser.add_argument("--z-max",
                        help="Non-inclusive maximum z frame to process. "
                             "Default is all",
                        type=int)
    parser.add_argument("--c",
                        help="Channels to process. Can be specified multiple "
                             "times. If none specified, do all.",
                        nargs="+")
    parser.add_argument("--t-min",
                        help="Minimum time frame to process. Default is all.",
                        type=int)
    parser.add_argument("--t-max",
                        help="Maximum time frame to process. Default is all.",
                        type=int)
    parser.add_argument("--series",
                        help="The series of images to be processed, starting "
                             "at zero. Hint - open it up in Fiji to see, then "
                             "subtract 1.",
                        type=int)
    parser.add_argument("--compression",
                        help="Compression to use when writing tiff files",
                        default=3,
                        type=int)
    return parser.parse_args(args)


def main(args=sys.argv[1:]):
    opts = parse_args(args)
    javabridge.start_vm(class_path=bioformats.JARS)
    try:
        with bioformats.ImageReader(opts.input) as rdr:
            if opts.series is not None:
                series = opts.series
                rdr.rdr.setSeries(series)
            else:
                series = 0
            n_c = rdr.rdr.getSizeC()
            n_z = rdr.rdr.getSizeZ()
            n_t = rdr.rdr.getSizeT()
            if opts.c is None or len(opts.c) == 0:
                c = range(n_c)
            else:
                c = opts.c
            if opts.z_min is None:
                z0 = 0
            else:
                z0 = opts.z_min
            if opts.z_max is None:
                z1 = n_z
            else:
                z1 = min(opts.z_max, n_z)
            if opts.t_min is None:
                t0 = 0
            else:
                t0 = opts.t_min
            if opts.t_max is None:
                t1 = n_t
            else:
                t1 = min(n_t, opts.t_max)
            for c, z, t in tqdm.tqdm(
                    list(itertools.product(c, range(z0, z1), range(t0, t1)))):
                img = rdr.read(c=c, z=z, t=t, series=series)
                path = opts.output_pattern.format(c=c, z=z, t=t)
                if not os.path.exists(os.path.dirname(path)):
                    os.mkdir(os.path.dirname(path))
                tifffile.imsave(path, img, compress=opts.compression)
    finally:
        javabridge.kill_vm()

if __name__ == "__main__":
    main()
