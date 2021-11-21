import numpy as np

from .model import SVDLightCurveModel, KilonovaGRBLightCurveModel


def create_light_curve_data(injection_parameters, args, doAbsolute=False):

    kilonova_kwargs = dict(model=args.kilonova_injection_model,
                           svd_path=args.kilonova_injection_svd,
                           mag_ncoeff=args.injection_svd_mag_ncoeff,
                           lbol_ncoeff=args.injection_svd_lbol_ncoeff)

    tc = injection_parameters['kilonova_trigger_time']
    tmin = args.kilonova_tmin
    tmax = args.kilonova_tmax
    tstep = args.kilonova_tstep
    detection_limit = {x: float(y) for x, y in zip(args.filters.split(","), args.injection_detection_limit.split(","))}
    filters = args.filters
    seed = args.generation_seed

    np.random.seed(seed)

    sample_times = np.arange(tmin, tmax + tstep, tstep)
    Ntimes = len(sample_times)

    if args.with_grb_injection:
        light_curve_model = KilonovaGRBLightCurveModel(sample_times=sample_times,
                                                       kilonova_kwargs=kilonova_kwargs,
                                                       GRB_resolution=np.inf)

    else:
        light_curve_model = SVDLightCurveModel(sample_times=sample_times,
                                               **kilonova_kwargs)

    lbol, mag = light_curve_model.generate_lightcurve(sample_times, injection_parameters)
    dmag = args.kilonova_error

    data = {}

    for filt in mag:
        mag_per_filt = mag[filt]
        if filt in detection_limit:
            det_lim = detection_limit[filt]
        else:
            det_lim = 0.0

        if not doAbsolute:
            mag_per_filt += 5. * np.log10(injection_parameters['luminosity_distance'] * 1e6 / 10.)
        data_per_filt = np.zeros([Ntimes, 3])
        for tidx in range(0, Ntimes):
            if mag_per_filt[tidx] >= det_lim:
                data_per_filt[tidx] = [sample_times[tidx] + tc, det_lim, np.inf]
            else:
                noise = np.random.normal(scale=dmag)
                data_per_filt[tidx] = [sample_times[tidx] + tc, mag_per_filt[tidx] + noise, dmag]
        data[filt] = data_per_filt

    return data
