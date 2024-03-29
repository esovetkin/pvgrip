from typing import Tuple

import celery
import pickle

from pvgrip.filter.tasks import apply_filter
from pvgrip.osm.tasks import map_raster_to_box
from pvgrip.utils.cache_fn_results \
    import call_cache_fn_results
from pvgrip.utils.cache_fn_results \
    import cache_fn_results
from pvgrip.utils.files \
    import get_tempfile, remove_file

from pvgrip.route.cluster_route_boxes \
    import get_list_rasters
from pvgrip.route.tasks \
    import compute_route, merge_tsv

from pvgrip.raster.calls \
    import check_all_data_available, sample_raster, convert_from_to
from pvgrip.raster.tasks \
    import sample_from_box, sample_from_points
from pvgrip.raster.utils \
    import check_box_not_too_big
from pvgrip.raster.mesh \
    import determine_epsg

from pvgrip.ssdp.utils \
    import centre_of_box

from pvgrip.storage.remotestorage_path \
    import searchandget_locally

from pvgrip.route.split_route \
    import split_route_calls
from pvgrip.osm.tasks import collect_json_dicts


def _max_box(rasters):
    if 0 == len(rasters):
        raise RuntimeError('length of rasters is 0!')

    res = rasters[0]['box']
    for x in rasters[1:]:
        res = [min(x['box'][0], res[0]),
               min(x['box'][1], res[1]),
               max(x['box'][2], res[2]),
               max(x['box'][3], res[3])]
    return res


def route_rasters(tsvfn_uploaded, box, box_delta, **kwargs):
    rasters_fn = get_list_rasters\
        (route_fn = searchandget_locally(tsvfn_uploaded),
         box = box, box_delta = box_delta)
    with open(searchandget_locally(rasters_fn),'rb') as f:
        rasters = pickle.load(f)

    kwargs['mesh_type'] = determine_epsg(_max_box(rasters), kwargs['mesh_type'])
    check_box_not_too_big(box = rasters[0]['box'],
                          step = kwargs['step'],
                          mesh_type = kwargs['mesh_type'])

    return check_all_data_available\
        (rasters = rasters, **kwargs), \
        rasters, kwargs['mesh_type']


@cache_fn_results()
def save_route(route):
    ofn = get_tempfile()
    try:
        with open(ofn, 'wb') as f:
            pickle.dump(route, f)
        return ofn
    except Exception as e:
        remove_file(ofn)


@split_route_calls(fn_arg = 'tsvfn_uploaded')
@call_cache_fn_results(minage = 1650884152)
def ssdp_route(tsvfn_uploaded, box, box_delta,
               dhi, ghi, albedo, timestr,
               offset, azimuth, zenith, nsky, **kwargs):
    tasks, rasters, kwargs['mesh_type'] = route_rasters\
        (tsvfn_uploaded = tsvfn_uploaded, box = box,
         box_delta = box_delta, **kwargs)

    group = []
    for x in rasters:
        route_fn = save_route(x['route'])

        lat, lon = centre_of_box(x['box'])
        group += \
            [sample_from_box.signature\
             (kwargs = {'box': x['box'],
                        'data_re': kwargs['data_re'],
                        'stat': kwargs['stat'],
                        'mesh_type': kwargs['mesh_type'],
                        'step': kwargs['step'],
                        'pdal_resolution': kwargs['pdal_resolution']},
              immutable = True) | \
             compute_route.signature\
             (kwargs = \
              {'route_fn': route_fn,
               'lat': lat,
               'lon': lon,
               'ghi_default': ghi,
               'dhi_default': dhi,
               'time_default': timestr,
               'offset_default': offset,
               'azimuth_default': azimuth,
               'zenith_default': zenith,
               'albedo': albedo,
               'nsky': nsky,
               'epsg': kwargs['mesh_type']})]
    tasks |= celery.group(group)
    tasks |= merge_tsv.signature()

    return tasks


@split_route_calls(fn_arg = 'tsvfn_uploaded',
                   merge_task = collect_json_dicts)
@call_cache_fn_results()
def render_raster_from_route(tsvfn_uploaded, box, box_delta,
                             do_filter, filter_type, filter_size, **kwargs):
    tasks, rasters, kwargs['mesh_type'] = route_rasters \
        (tsvfn_uploaded=tsvfn_uploaded, box=box,
         box_delta=box_delta, **kwargs)

    output_type = kwargs['output_type']
    del kwargs['output_type']
    do_filter = 'yes' == do_filter

    group = []
    for raster in rasters:
        x = sample_raster(
            box=raster['box'],
            output_type='pickle' if do_filter else output_type,
            **kwargs)

        if do_filter:
            x |= apply_filter.signature\
                (kwargs={'filter_type': filter_type,
                         'filter_size': filter_size})
            x = convert_from_to(x, from_type="pickle",
                                to_type = output_type,
                                scale_name='m')

        x |= map_raster_to_box.signature\
            (kwargs={"box": raster["box"]})
        group += [x]
    tasks |= celery.group(group)
    tasks |= collect_json_dicts.signature()

    return tasks


@split_route_calls(fn_arg = 'tsvfn_uploaded')
@call_cache_fn_results()
def query_raster_value(tsvfn_uploaded, **kwargs):
    """

    :tsvfn_uploaded: must contain route coordinates with longitude and latitude columns

    :kwargs: contains pdal_resolution, stat, data_re

    """
    # each element in rasters will queue at most 1 + 3? files,
    # assuming each raster is no larger than 1x1 km^2
    tasks, rasters, _ = route_rasters\
        (tsvfn_uploaded,
         box = [-1,-1,1,1],
         box_delta = 1000,
         mesh_type = 'utm',
         step = 1, **kwargs)

    group = []
    for x in rasters:
        route_fn = save_route(x['route'])

        group += [sample_from_points.signature\
                  (kwargs = {'route_fn': route_fn,
                             'box': x['box'],
                             'data_re': kwargs['data_re'],
                             'stat': kwargs['stat'],
                             'pdal_resolution': kwargs['pdal_resolution']},
                   immutable = True)]
    tasks |= celery.group(group)
    tasks |= merge_tsv.signature()

    return tasks
