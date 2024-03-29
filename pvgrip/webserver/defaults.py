from pvgrip.utils.format_dictionary \
    import format_dictionary

from pvgrip.weather.copernicus \
    import reanalysis_era5_variables


def calls_help():
    return """
    Query geo-spatial data

    /api/help            print this page
    /api/help/<what>     print help for <what>

    /api/datasets        list available datasets

    /api/upload          upload a file to the storage
    /api/download        upload a file from the storage

    /api/raster          get a raster image of a region

        /api/raster/route
                         get raster image values from coordinates specified in a route

    /api/irradiance      compute irradiance raster map.

        Several library bindings are available (default ssdp):
        /api/irradiance/ssdp
                         use the SSDP library to compute irradiance maps

        /api/irradiance/grass
                         use the GRASS library

    /api/route           compute irradiance along a route

        /api/route/render  render raster images along a route

    /api/integrate       integrate irradiance map over a period of time

    /api/shadow          compute binary map of a shadow at a time of a region

        /api/shadow/average
                         compute average value of shadows over given times

    /api/osm             render binary images of rendered from OSM

        /api/osm/rules   create a colour rules file by collecting all
                         pairs of tags:values from the OSM data along
                         a given route

        /api/osm/route   render a route from OSM by using a rulesfile

    /api/weather         get various weather data

        /api/weather/irradiance/{route,box}
                         get irradiance values for a route or region
        /api/weather/reanalysis/{route,box}
                         get various reanalysis data

    /api/filter          apply various filters with raster data

        /api/filter/raster/{route,box}
                         sample raster and apply a filter

        /api/filter/lidar_stdev/{route,box}
                         compute stdev of lidar points in any window

    /api/status          print current active and scheduled jobs

    """


def global_defaults():
    return {'serve_type': \
            ('file',
             """
             type of output to serve

             choice: ("file","path","ipfs_cid")

              - "file": webserver sends back a file
              - "path": webserver sends back a pvgrip path
                    a file can be downloaded with /download
              - "ipfs_cid": webserver sends back an ipfs_cid
                    a file can be downloaded through ipfs""")}


def lookup_defaults():
    res = global_defaults()
    res.update({'location': \
                ([50.87,6.12],
                 '[latitude, longitude] of the desired location'),
                'data_re': \
                (r'.*',
                 'regular expression matching the dataset'),
                'stat': \
                ('max',
                 """
                 statistic to compute for LAS files

                 choice: ("max","min","mean","idw","count","stdev")"""),
                'pdal_resolution': \
                (0.3,
                 """
                 resolution with what to sample LAS files
                 """)})
    return res


def raster_defaults():
    res = lookup_defaults()
    del res['location']
    res.update({'box': \
                ([50.865,7.119,50.867,7.121],
                 """
                 bounding box of desired locations

                 format: [lat_min, lon_min, lat_max, lon_max]"""),
                'step': \
                (float(1),
                 'resolution of the sampling mesh in meters'),
                'mesh_type': \
                ('utm',
                 """coordinate system to use for the mesh

                 either an epsg code, or 'utm':

                   - '4326' is World Geodetic System 1984 (WGS84) used
                     in GPS

                   - 'utm' is Universal Transverse Mercator coordinate
                     system, that select coordinate system
                     automatically, depending on the locations of
                     interest. This is an enforced option for all
                     procedures the requires metric coordinates.

                 beware to use 'utm' (default) for any computations
                 where one requires accurate meters for coordinates!"""),
                'output_type': \
                ('pickle',
                 """
                 type of output

                 choices: "pickle","geotiff","pnghillshade","png","pngnormalize","pngnormalize_scale"

                 "png" does not normalise data""")})
    return res


def timestr_argument():
    return {'timestr': \
            ("2020-07-01_06:00:00",
             "UTC time of the shadow")}


def shadow_defaults():
    res = raster_defaults()
    res.update({
        'what': \
        ('shadow',
         """
         what to compute

         choices: "shadow", "incidence"

         the incidence map always produces geotiff
         shadow produces a binary shadow map""")})
    res.update(timestr_argument())
    return res


def shadow_average_defaults():
    res = raster_defaults()
    res.update({
        'timestrs_fn': \
        ('NA',
        """a pvgrip path resulted from /api/upload

        The tsv file must contain a header with at least
        'timestr', where every time is given in the format.

        %Y-%m-%d_%H:%M:%S
        e.g.
        2020-07-01_06:00:00

        Note, in case csv contains a single column, wrap the column
        name in quotes, otherwise this might happen:
        https://github.com/pandas-dev/pandas/issues/17333""")})
    return res


def _del_for_osm(x):
    for what in ('stat', 'data_re', 'pdal_resolution'):
        if what in x:
            del x[what]

    return x


def _rules_fn(res):
    res.update({
        "rules_fn":
        ("NA",
         """path to a rules file

         Path to a json of type Dict[str, Dict[str, Tuple[int,
         str]]. It is a map of osm tags to a map of osm tag:values to a
         List/Tuple, where the first entry if the number of occurrences
         and the second entry is the hexcolor (hexcolor form:
         #[0-9a-f]{6}).
         
         The order of the keys of the outer dict (the osm tags) determine the order of the rendering.
         E.g. if natural is before building then natural will be painted first and building will be painted over them.
         If natural is before building then first buildings are painted and then natural will be painted over
         potentially covering the buildings.
        
         File can be uploaded directly or an output of osm/rules can be
         used.

         If NA or no path if provided then it will default to the
         /usr/local/share/smrender/rules_land.osm rules file.""")})
    return res


def osm_defaults():
    res = raster_defaults()
    res = _del_for_osm(res)
    res = _rules_fn(res)
    return res


def osm_rules_defaults():
    res = _route()
    res = _del_for_osm(res)

    for what in ('step', 'mesh_type'):
        if what in res:
            del res[what]

    res.update({
        "tags":
        (["natural", "landuse", "highway", "building"],
         """
         List of openstreetmap tags to fetch keys for.
         The order of the tags determines the order of the rendering.
         e.g. for the default building will be drawn last atop of first
         highway then landuse and then lastly natural.
         """)})
    return res


def osm_route_defaults():
    res = _route(with_output_type = True)
    res = _del_for_osm(res)
    res = _rules_fn(res)
    return res


def irradiance_defaults():
    res = shadow_defaults()
    del res['what']
    del res['output_type']
    res.update({
        'rsun_args': \
        ({'aspect_value': float(270),
          'slope_value': float(0)},
         """Arguments passed to r.sun.

         Raster arguments are not currently supported""")
    })
    return res


def upload_defaults():
    return {'data': \
            ('NA',
             """a local path for a file to upload

             Must be specified as a form element.

             For example, for a local file '/files/example.txt', say
             curl -F data=@/files/example.txt <site>/api/upload
             """)}


def download_defaults():
    res = global_defaults()
    res.update({
        'path': \
        ('NA',
         """a storage path for a file to download
         """)})
    return res


def ssdp_defaults():
    res = raster_defaults()

    res.update({'ghi': \
                (float(1000),
                 "Global horizontal irradiance"),
                'dhi': \
                (float(100),
                 "Diffused horizontal irradiance"),
                'albedo':
                (0.5,
                 "albedo value between 0-1"),
                'offset':
                (float(0),
                 "offset in meters in the direction of the surface normal"),
                'azimuth':
                (float(0),
                 """azimuth angle in degrees of the tilted surface.
                 The azimuth angle is set wrt the surface normal.

                 North:   0 degrees
                 South: 180 degrees
                 East:   90 degrees
                 West:  270 degrees
                 """),
                'zenith':
                (float(0),
                 """zenith angle in degrees of the tilted surface
                 The zenith angle is set wrt the surface normal.

                 Zenith angle of 0 degrees corresponds to the vertical direction.
                 """),
                'nsky':
                (10,
                 """The  number  of  zenith  discretizations.

                 The  total number of sky patches equals
                 Ntotal(N)=3N(N-1)+1,
                 e.g. with Ntotal(7)=127

                 Based on POA simulations without topography: 7 is
                 good enough, 10 noticeably better. Beyond that it is
                 3rd significant digit improvements.
                 """)})
    res.update(timestr_argument())
    return res


def _route(with_output_type = False):
    res = raster_defaults()

    if not with_output_type:
        del res['output_type']

    res.update({'box': \
                ([-50,-50,50,50],
                 """
                 bounding box steps around each location in meters

                 format: [east,south,west,north]

                 """),
                'box_delta': \
                (3,
                 """a constant that defines a maximum raster being sampled

                 For example, if a 'box' is a rectangle with sizes
                 a x b, then the maximum sized raster being sampled has
                 dimensions: a*2*box_delta x b*2*box_delta.

                 The constant is replaced with max(1,box_delta).

                 """),
                'tsvfn_uploaded': \
                ('NA',
                 """a pvgrip path resulted from /api/upload

                 The tsv file must contain a header with at least
                 'latitude' and 'longitude' columns.
                 """)})
    return res


def raster_route_defaults():
    res = _route()

    del res['box']
    del res['box_delta']
    del res['step']
    del res['mesh_type']

    return res


def route_defaults():
    res = ssdp_defaults()
    res.update(_route())
    res.update({'tsvfn_uploaded': \
                ('NA',
                 """a pvgrip path resulted from /api/upload

                 The tsv file must contain a header with at least
                 'latitude' and 'longitude' columns.

                 The following columns are optional: 'ghi', 'dhi',
                 'timestr'. In case some of the columns are missing, a
                 constant value for all locations is used.

                 """)})
    return res


def route_render_defaults():
    res = _route(with_output_type = True)
    res.update(_filter_type())
    res.update({
        'do_filter': \
        ('no',
         """if "yes", then apply filter
         """)})

    return res


def integrate_defaults():
    res = ssdp_defaults()

    res.update({'tsvfn_uploaded': \
                ('NA',
                 """a pvgrip path resulted from /api/upload

                 The tsv file must contain a header with 'timestr',
                 'ghi' and 'dhi' columns.

                 """)})
    del res['ghi']
    del res['dhi']
    del res['timestr']
    return res


def _irradiance_options():
    return {
        'what': \
        (['GHI','DHI'],
         """what to get

         Options are:

         - 'TOA' Irradiation on horizontal plane at the top of
            atmosphere (W/m2)

          - 'Clear sky GHI' Clear sky global irradiation on horizontal
            plane at ground level (W/m2)

          - 'Clear sky BHI' Clear sky beam irradiation on horizontal
            plane at ground level (W/m2)

          - 'Clear sky DHI' Clear sky diffuse irradiation on
            horizontal plane at ground level (W/m2)

          - 'Clear sky BNI' Clear sky beam irradiation on mobile plane
            following the sun at normal incidence (W/m2)

          - 'GHI' Global irradiation on horizontal plane at ground
            level (W/m2)

          - 'BHI' Beam irradiation on horizontal plane at ground level
            (W/m2)

          - 'DHI' Diffuse irradiation on horizontal plane at ground
            level (W/m2)

          - 'BNI' Beam irradiation on mobile plane following the sun
            at normal incidence (W/m2)

         """)}


def _reanalysis_options():
    return {
        'what': \
        (['10m_u_component_of_wind',
          '10m_v_component_of_wind',
          '2m_temperature'],
         """what to get

         Options are:

         {}

         """.format(reanalysis_era5_variables))
    }


def weather_irradiance_route():
    res = global_defaults()
    res.update(_irradiance_options())
    res.update({
        'tsvfn_uploaded': \
        ('NA',
         """a pvgrip path resulted from /api/upload

         The tsv file must contain a header with at least
         'latitude', 'longitude' and 'timestr' columns.
         """)})
    return res


def weather_irradiance_box():
    res = global_defaults()
    res.update(_irradiance_options())
    res.update({
        'box': \
        ([50.865,7.119,50.867,7.121],
         """
         bounding box of desired locations

         format: [lat_min, lon_min, lat_max, lon_max]"""),
        'time_range': \
        ('2019-07-01_10:00:00/2019-07-01_11:00:00',
         """a string specifying a time range in UTC

         It can be either in the format:
         '%Y-%m-%d_%H:%M:%S/%Y-%m-%d_%H:%M:%S'
         specifying a true range, or
         '%Y-%m-%d_%H:%M:%S'
         specifying a single time
         """),
        'time_step': \
        ('20minutes',
         """a string specifying a time step

         Format: '<integer><units>',
         where unit is second, minute, hour or day (or plural)
         """)})
    return res


def weather_reanalysis_route():
    res = global_defaults()
    res.update(_reanalysis_options())
    res.update({
        'tsvfn_uploaded': \
        ('NA',
         """a pvgrip path resulted from /api/upload

         The tsv file must contain a header with at least
         'latitude', 'longitude' and 'timestr' columns.
         """)})
    return res


def weather_reanalysis_box():
    res = global_defaults()
    res.update(_reanalysis_options())
    res.update({
        'box': \
        ([50.865,7.119,50.867,7.121],
         """
         bounding box of desired locations

         format: [lat_min, lon_min, lat_max, lon_max]"""),
        'time_range': \
        ('2019-07-01_10:00:00/2019-07-01_11:00:00',
         """a string specifying a time range in UTC

         It can be either in the format:
         '%Y-%m-%d_%H:%M:%S/%Y-%m-%d_%H:%M:%S'
         specifying a true range, or
         '%Y-%m-%d_%H:%M:%S'
         specifying a single time
         """),
        'time_step': \
        ('20minutes',
         """a string specifying a time step

         Format: '<integer><units>',
         where unit is second, minute, hour or day (or plural)
         """)})
    return res


def _filter():
    return {'filter_size': \
            ([20,20],
             """
             arguments defines width and heihgt
             (in meters) of the area variance is computed
             """)}


def _filter_type():
    res = _filter()
    res.update({'filter_type': \
                ('average_per_sqm',
                 """type of filter to apply. options:

                 - average_per_sqm (average per m^2)
                 - sum
                 - average_in_filter (average in filer with size (filer_size[0]*step, filter_size[1]*step)
                 """)})
    return res


def filter_lidar_stdev():
    res = raster_defaults()
    del res['stat']
    res.update(_filter())
    return res


def filter_raster():
    res = raster_defaults()
    res.update(_filter_type())
    return res


def _filter_route():
    return {'neighbour_step':
            ([30,30],
             """step at each neigbours in the route point are selected

             9 neighbours are selected:
             nw, nc, ne
             cw, cc, ce
             sw, sc, se

             """),
            'azimuth':
            (0,
             """
             angle at which neighbours are selected

             azimuth zero, then 'nc' neighbour is truly 'nc'
             """)}


def filter_lidar_stdev_route():
    res = _route()
    del res['stat']
    res.update(_filter())
    res.update(_filter_route())
    return res


def filter_raster_route():
    res = _route()
    res.update(_filter_type())
    res.update(_filter_route())
    return res


def call_defaults(method):
    if 'raster' == method:
        res = raster_defaults()
    elif 'raster/route' == method:
        res = raster_route_defaults()
    elif 'shadow' == method:
        res = shadow_defaults()
    elif 'shadow/average' == method:
        res = shadow_average_defaults()
    elif 'irradiance' == method:
        res = ssdp_defaults()
    elif 'irradiance/ssdp' == method:
        res = ssdp_defaults()
    elif 'irradiance/grass' == method:
        res = irradiance_defaults()
    elif 'osm' == method:
        res = osm_defaults()
    elif "osm/rules" == method:
        res = osm_rules_defaults()
    elif "osm/route" == method:
        res = osm_route_defaults()
    elif "ssdp" == method:
        res = ssdp_defaults()
    elif 'upload' == method:
        res = upload_defaults()
    elif 'download' == method:
        res = download_defaults()
    elif 'route' == method:
        res = route_defaults()
    elif "route/render" == method:
        res = route_render_defaults()
    elif "integrate" == method:
        res = integrate_defaults()
    elif 'weather/irradiance' == method:
        res = weather_irradiance_box()
    elif 'weather/irradiance/box' == method:
        res = weather_irradiance_box()
    elif 'weather/irradiance/route' == method:
        res = weather_irradiance_route()
    elif 'weather/reanalysis' == method:
        res = weather_reanalysis_box()
    elif 'weather/reanalysis/box' == method:
        res = weather_reanalysis_box()
    elif 'weather/reanalysis/route' == method:
        res = weather_reanalysis_route()
    elif 'filter/lidar_stdev' == method:
        res = filter_lidar_stdev()
    elif 'filter/lidar_stdev/box' == method:
        res = filter_lidar_stdev()
    elif 'filter/lidar_stdev/route' == method:
        res = filter_lidar_stdev_route()
    elif 'filter/raster' == method:
        res = filter_raster()
    elif 'filter/raster/box' == method:
        res = filter_raster()
    elif 'filter/raster/route' == method:
        res = filter_raster_route()
    else:
        return None

    return res
