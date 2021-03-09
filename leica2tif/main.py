# Built-in imports
from pathlib import Path
import argparse
import itertools
import struct
import pdb
import sys
import os

# Third-party imports
import bioformats
import numpy as np
import javabridge
import tifffile
import tqdm


# Lookup tables (LUTs) for imagej tiffstack
val_range = np.arange(256, dtype='uint8')
GRAY = np.tile(np.arange(256, dtype='uint8'), (3, 1))
RED = np.zeros((3, 256), dtype='uint8')
RED[0] = val_range
GREEN = np.zeros((3, 256), dtype='uint8')
GREEN[1] = val_range
BLUE = np.zeros((3, 256), dtype='uint8')
BLUE[2] = val_range
YELLOW = np.zeros((3, 256), dtype='uint8')
YELLOW[[0,1],:] = val_range
MAGENTA = np.zeros((3, 256), dtype='uint8')
MAGENTA[[0,2],:] = val_range
CYAN = np.zeros((3, 256), dtype='uint8')
CYAN[[1,2],:] = val_range
LUT_CYCLE = [BLUE, RED, GREEN, YELLOW, CYAN, MAGENTA, GRAY]



# from here: https://stackoverflow.com/questions/50258287/how-to-specify-colormap-when-saving-tiff-stack
def imagej_metadata_tags(metadata, byteorder):
    """Return IJMetadata and IJMetadataByteCounts tags from metadata dict.
    The tags can be passed to the TiffWriter.save function as extratags.
    """
    header = [{'>': b'IJIJ', '<': b'JIJI'}[byteorder]]
    bytecounts = [0]
    body = []

    def writestring(data, byteorder):
        return data.encode('utf-16' + {'>': 'be', '<': 'le'}[byteorder])

    def writedoubles(data, byteorder):
        return struct.pack(byteorder+('d' * len(data)), *data)

    def writebytes(data, byteorder):
        return data.tobytes()

    metadata_types = (
        ('Info', b'info', 1, writestring),
        ('Labels', b'labl', None, writestring),
        ('Ranges', b'rang', 1, writedoubles),
        ('LUTs', b'luts', None, writebytes),
        ('Plot', b'plot', 1, writebytes),
        ('ROI', b'roi ', 1, writebytes),
        ('Overlays', b'over', None, writebytes))

    for key, mtype, count, func in metadata_types:
        if key not in metadata:
            continue
        if byteorder == '<':
            mtype = mtype[::-1]
        values = metadata[key]
        if count is None:
            count = len(values)
        else:
            values = [values]
        header.append(mtype + struct.pack(byteorder+'I', count))
        for value in values:
            data = func(value, byteorder)
            body.append(data)
            bytecounts.append(len(data))

    body = b''.join(body)
    header = b''.join(header)
    data = header + body
    bytecounts[0] = len(header)
    bytecounts = struct.pack(byteorder+('I' * len(bytecounts)), *bytecounts)
    return ((50839, 'B', len(data), data, True),
            (50838, 'I', len(bytecounts)//4, bytecounts, True))


def parse_args(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",
                        help=".lif file to be read",
                        required=True)
    parser.add_argument("--info", action='store_true',
                        help="Get only OMEXML metadata information")
    parser.add_argument("--output-pattern",
                        help="Output pattern for files, with format escapes "
                             "for z, t and c, e.g. "
                             "\"/path-to/img_z{z:04d}_c{c:01d}_t{t:04d}.tiff",
                        default='img_z{z:04d}_c{c:01d}_t{t:04d}.tiff')
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
                             "subtract 1. 'all' for extracting all series",
                        type=str,
                        default='0')
    parser.add_argument("--compression",
                        help="Compression to use when writing tiff files.",
                        default=3,
                        type=int)
    parser.add_argument("--dtype",
                        help="The numpy pixel datatype")
    parser.add_argument("--stack", action='store_true',
                        help="Output is a single collated tiff: imagej hyperstack.")
    parser.add_argument("--output", 
                        help="A single output filename for the collated tiff stack.",
                        default="./output{srs:03d}.tiff")
    return parser.parse_args(args)


def parse_series(arg_series):
    series = []
    for s in arg_series.split(','):
        r = s.strip().split('-')
        if len(r) == 1:
            series += r
        elif len(r) == 2:
            series += list(range(int(r[0]), int(r[1])+1)) 
        else:
            raise ValueError
    return list(map(int, series))
        

def main(args=sys.argv[1:]):
    opts = parse_args(args)
    javabridge.start_vm(class_path=bioformats.JARS)
    try:
        # Get omexml metadata stored in the lif file
        omemeta = bioformats.omexml.OMEXML(bioformats.get_omexml_metadata(opts.input))
        n_images = omemeta.get_image_count()
        if opts.series == 'all':
            series = '0-%d'%(n_images - 1)
        else: 
            series = opts.series
        series = parse_series(series)


        for srs in series:
            meta = omemeta.image(srs)
            name = meta.get_Name()
            n_t = meta.Pixels.SizeT
            n_z = meta.Pixels.SizeZ
            n_c = meta.Pixels.SizeC
            n_y = meta.Pixels.SizeY
            n_x = meta.Pixels.SizeX
            physical_size_x = meta.Pixels.get_PhysicalSizeX()
            physical_size_x_unit = meta.Pixels.get_PhysicalSizeXUnit()
            physical_size_y = meta.Pixels.get_PhysicalSizeY()
            physical_size_y_unit = meta.Pixels.get_PhysicalSizeYUnit()
            physical_size_z = meta.Pixels.get_PhysicalSizeZ()
            physical_size_z_unit = meta.Pixels.get_PhysicalSizeZUnit()
            dimension_order = meta.Pixels.get_DimensionOrder()
            pxtype = meta.Pixels.get_PixelType()

            if opts.info:
                print("""
                    Series: {}
                    Image name: {}
                    Dimensions: {}, {}
                    Physical size X: {}
                    Physical size Y: {}
                    Physical size Z: {}
                    Physical size unit: {}
                    Pixel type: {}
                """.format( srs, name, dimension_order, 'x'.join(map(str, [n_x, n_y, n_c, n_z, n_t])),
                            physical_size_x, physical_size_y, physical_size_z, physical_size_x_unit,
                            pxtype ).replace('  ',''))
                continue

            rdr = bioformats.ImageReader(opts.input)

            # Through following command one may get other metadata such as microscope settings
            # jdict(rdr.rdr.getSeriesMetadata())

            if opts.c is None or len(opts.c) == 0:
                ch = range(n_c)
            else:
                ch = opts.c
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

            if opts.stack: img_stack = None
            iterator = list(itertools.product(ch, range(z0, z1), range(t0, t1)))
            for i, (c, z, t) in tqdm.tqdm(
                    enumerate(iterator), total=len(iterator)):
                img = rdr.read(c=c, z=z, t=t, series=srs)

                if opts.dtype is not None:
                    try: vmax = np.iinfo(opts.dtype).max
                    except ValueError: vmax = 1.0

                    if img.dtype.name.startswith("float"):
                        img = img * vmax

                    img = img.astype(opts.dtype)

                dtype = opts.dtype or img.dtype

                # imagej hyperstack must be in TZCYXS order
                if opts.stack:
                    if i == 0:
                        img_stack = np.zeros([t1-t0, z1-z0, len(ch), *img.shape], dtype=dtype)
                    img_stack[t, z, c, ...] = img

                else:
                    path = Path(name)/opts.output_pattern.format(c=c, z=z, t=t)
                    if not os.path.exists(os.path.dirname(path)):
                        os.mkdir(os.path.dirname(path))
                    tifffile.imsave(path, img, compress=opts.compression)

            if opts.stack:
                path = opts.output.format(srs=srs)
                if not os.path.exists(os.path.dirname(path)):
                    os.mkdir(os.path.dirname(path))

                ijmeta = {'spacing': physical_size_z, 'unit': 'micron', 'axes':'TZCYX', 'mode':'composite'}
                ijtags = imagej_metadata_tags({'LUTs':LUT_CYCLE[:len(ch)]}, '>') 

                tifffile.imwrite(path, img_stack, compress=opts.compression, byteorder='>',
                                 imagej=True, resolution=(1./physical_size_y, 1./physical_size_x),
                                 metadata=ijmeta, extratags=ijtags)
    finally:
        javabridge.kill_vm()

if __name__ == "__main__":
    main()
