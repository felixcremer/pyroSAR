##############################################################
# ancillary routines for software pyroSAR
# John Truckenbrodt 2014-2018
##############################################################
"""
This script gathers central functions and classes for general pyroSAR applications.
"""
import os
import re
from datetime import datetime
from ._dev_config import product_pattern

try:
    import pathos.multiprocessing as mp
except ImportError:
    pass

from spatialist.ancillary import finder


def groupby(images, attribute):
    """
    group a list of images by a metadata attribute
    
    Parameters
    ----------
    images: list of str
        the names of the images to be sorted
    attribute: str
        the name of the attribute used for sorting;
        see :func:`parse_datasetname` for options
    
    Returns
    -------
    list of lists
        a list containing a list with image names ofr each group
    """
    images_sort = sorted(images, key=lambda x: re.search(product_pattern, x).group(attribute))
    out_meta = [[parse_datasetname(images_sort.pop(0))]]
    while len(images_sort) > 0:
        filename = images_sort.pop(0)
        meta = parse_datasetname(filename)
        
        if out_meta[-1][0][attribute] == meta[attribute]:
            out_meta[-1].append(meta)
        else:
            out_meta.append([meta])
    out = [[x['filename'] for x in y] for y in out_meta]
    return out


def groupbyTime(images, function, time):
    """
    function to group images by their acquisition time difference

    Parameters
    ----------
    images: list of str
        a list of image names
    function: function
        a function to derive the time from the image names; see e.g. :func:`seconds`
    time: int or float
        a time difference in seconds by which to group the images

    Returns
    -------
    list
        a list of sub-lists containing the grouped images
    """
    # sort images by time stamp
    srcfiles = sorted(images, key=function)
    
    groups = [[srcfiles[0]]]
    group = groups[0]
    
    for i in range(1, len(srcfiles)):
        item = srcfiles[i]
        timediff = abs(function(item) - function(group[-1]))
        if timediff <= time:
            group.append(item)
        else:
            groups.append([item])
            group = groups[-1]
    return [x[0] if len(x) == 1 else x for x in groups]


def seconds(filename):
    """
    function to extract time in seconds from a file name.
    the format must follow a fixed pattern: YYYYmmddTHHMMSS
    Images processed with pyroSAR functionalities via module snap or gamma will contain this information.

    Parameters
    ----------
    filename: str
        the name of a file from which to extract the time from

    Returns
    -------
    float
        the difference between the time stamp in filename and Jan 01 1900 in seconds
    """
    # return mktime(strptime(re.findall('[0-9T]{15}', filename)[0], '%Y%m%dT%H%M%S'))
    td = datetime.strptime(re.findall('[0-9T]{15}', filename)[0], '%Y%m%dT%H%M%S') - datetime(1900, 1, 1)
    return td.total_seconds()


def parse_datasetname(name, parse_date=False):
    """
    Parse the name of a pyroSAR processing product and extract its metadata components as dictionary
    
    Parameters
    ----------
    name: str
        the name of the file to be parsed
    parse_date: bool
        parse the start date to a :class:`~datetime.datetime` object or just return the string?
    
    Returns
    -------
    dict
        the metadata attributes
    
    Examples
    --------
    >>> meta = parse_datasetname('S1A__IW___A_20150309T173017_VV_grd_mli_geo_norm_db.tif')
    >>> print(list(meta.keys()))
    ['sensor', 'acquisition_mode', 'orbit', 'start', 'extensions', 'polarization', 'proc_steps']
    """
    
    filename = os.path.realpath(name)
    
    match = re.match(re.compile(product_pattern), filename)
    if not match:
        return
    out = match.groupdict()
    if out['extensions'] == '':
        out['extensions'] = None
    if len(out['proc_steps']) > 0:
        out['proc_steps'] = out['proc_steps'].split('_')
    else:
        out['proc_steps'] = None
    if parse_date:
        out['start'] = datetime.strptime(out['start'], '%Y%m%dT%H%M%S')
    out['filename'] = filename
    return out


def find_datasets(directory, recursive=False, **kwargs):
    """
    find pyroSAR datasets in a directory based on their metadata
    
    Parameters
    ----------
    directory: str
        the name of the directory to be searched
    recursive: bool
        search the directory recursively into subdirectories?
    kwargs:
        Metadata attributes for filtering the scene list supplied as `key=value`. e.g. `sensor='S1A'`.
        Multiple allowed options can be provided in tuples, e.g. `sensor=('S1A', 'S1B')`.
        Any types other than tuples require an exact match, e.g. `proc_steps=['grd', 'mli', 'geo', 'norm', 'db']`
        will be matched if only these processing steps are contained in the product name in this exact order.
        See function :func:`parse_productname` for options.
    
    Returns
    -------
    list of str
        the file names found in the directory and filtered by metadata attributes
    
    Examples
    --------
    >>> selection = find_datasets('path/to/files', sensor=('S1A', 'S1B'), polarization='VV')
    """
    files = finder(directory, [product_pattern], regex=True, recursive=recursive)
    selection = []
    for file in files:
        meta = parse_datasetname(file)
        match = True
        for key, val in kwargs.items():
            if isinstance(val, tuple):
                match = meta[key] in val
            else:
                match = meta[key] == val
        if match:
            selection.append(file)
    return selection
