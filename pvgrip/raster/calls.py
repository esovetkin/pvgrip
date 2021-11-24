import celery

from pvgrip.utils.cache_fn_results \
    import call_cache_fn_results

from pvgrip.storage.remotestorage_path \
    import searchif_instorage

from pvgrip.globals \
    import get_SPATIAL_DATA

from pvgrip.lidar.calls \
    import process_laz

from pvgrip.raster.tasks \
    import save_png, save_geotiff, \
    save_pnghillshade, save_pickle, \
    sample_from_box
from pvgrip.raster.utils \
    import check_box_not_too_big, index2fn


def check_all_data_available(**kwargs):
    SPATIAL_DATA = get_SPATIAL_DATA()
    index = SPATIAL_DATA.subset\
        (**{k:v for k,v in kwargs.items()
            if k in ('data_re','box','rasters')})

    tasks = []
    for x in index.iterate():
        fn = index2fn\
            (x, stat = kwargs['stat'],
             pdal_resolution = kwargs['pdal_resolution'])

        if searchif_instorage(fn):
            continue

        if 'remote_meta' in x:
            tasks += [process_laz\
                      (url = x['url'],
                       ofn = x['file'],
                       resolution = kwargs['pdal_resolution'],
                       what = kwargs['stat'],
                       if_compute_las = x['if_compute_las'])]
            continue

        raise RuntimeError('%s file is not available'\
                           % x['file'])
    return celery.group(tasks)


def _convert_from_pickle(tasks, output_type):
    if output_type not in ('geotiff', 'pickle',
                           'pnghillshade','png',
                           'pngnormalize'):
        raise RuntimeError("Invalid 'output_type' argument!")

    if output_type == 'png':
        tasks |= save_png.signature()
        return tasks

    if output_type == 'pngnormalize':
        tasks |= save_png.signature(kwargs = {'normalize': True})
        return tasks

    if output_type in ('geotiff', 'pnghillshade'):
        tasks |= save_geotiff.signature()

    if output_type == 'pnghillshade':
        tasks |= save_pnghillshade.signature()

    return tasks


def convert_from_to(tasks, from_type, to_type):
    if 'pickle' == from_type:
        if 'pickle' == to_type:
            return tasks

        return _convert_from_pickle(tasks, to_type)

    if 'geotiff' == from_type:
        if 'geotiff' == to_type:
            return tasks

        if 'pnghillshade' == to_type:
            return tasks | save_pnghillshade.signature()

        tasks = tasks | save_pickle.signature()


    return _convert_from_pickle(tasks, to_type)


@call_cache_fn_results()
def sample_raster(box, data_re, stat,
                  mesh_type, step, output_type,
                  pdal_resolution):
    check_box_not_too_big(box = box, step = step,
                          mesh_type = mesh_type)

    if stat not in ("max","min","count","mean","idw","stdev"):
        raise RuntimeError("""invalid stat = {}
        allowed values: ("max","min","count","mean","idw","stdev")
        """.format(stat))

    if pdal_resolution <= 0:
        raise RuntimeError("invalid pdal_resolution = {}"\
                           .format(pdal_resolution))

    tasks = celery.chain\
        (check_all_data_available\
         (box = box,
          data_re = data_re,
          stat = stat,
          pdal_resolution = pdal_resolution),\
         sample_from_box.signature\
         (kwargs = {'box': box,
                    'data_re': data_re,
                    'stat': stat,
                    'mesh_type': mesh_type,
                    'step': step,
                    'pdal_resolution': pdal_resolution},
          immutable = True))

    return convert_from_to(tasks,
                           from_type = 'pickle',
                           to_type = output_type)
