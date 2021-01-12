import pickle
import numpy as np

from osgeo import gdal
from osgeo import gdal_array
from osgeo import osr

from celery_once import QueueOnce

import open_elevation.celery_tasks.app as app


def _save_geotiff(data, ofn):
    """Save data array to geotiff

    taken from: https://gis.stackexchange.com/a/37431
    see also: http://osgeo-org.1560.x6.nabble.com/gdal-dev-numpy-array-to-raster-td4354924.html

    :data: output of _sample_from_box

    :ofn: name of the output file
    """
    array = data['raster']

    xmin, ymin, xmax, ymax = data['mesh']['raster_box']
    nrows, ncols = array.shape
    xres = (xmax - xmin)/float(ncols)
    yres = (ymax - ymin)/float(nrows)
    geotransform = (xmin, xres, 0, ymax, 0, -yres)

    output_raster = gdal.GetDriverByName('GTiff')\
                        .Create(ofn, ncols, nrows,
                                1, gdal.GDT_Float32)
    output_raster.SetGeoTransform(geotransform)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(data['mesh']['epsg'])

    output_raster.SetProjection(srs.ExportToWkt())
    output_raster.GetRasterBand(1).WriteArray(data['raster'])
    output_raster.FlushCache()


@app.CELERY_APP.task(base=QueueOnce)
def save_geotiff(pickle_fn):
    ofn = app.RESULTS_CACHE.get((pickle_fn), check=False)
    if app.RESULTS_CACHE.file_in(ofn):
        return ofn

    with open(pickle_fn, 'rb') as f:
        data = pickle.load(f)
    _save_geotiff(data, ofn)
    app.RESULTS_CACHE.add_file(ofn)
    return ofn
