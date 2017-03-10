Optimizations with pyrocko and kite  
========================================

Leeds notice:
We will need the pyrocko:master, kite:dev branch and grond:refactor branch.

Introduction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For both the dynamic waveform and static displacment data a earthquake source optimization is shown.
Using the :py:class:`pyrocko.gf.seismosizer.DCSource` for the dynamic waveforms and a
:py:class:`pyrocko.gf.seismosizer.RectangularSource` for the static optimization as source.

For each two example are shown, one to carry out the optimization from the command console
and one from script.



For this tutorial the software packages of Grond are needed in addtion to the
Pyrocko installation with all its dependencies.


Dynamic waveform optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Dynamic waveform optimization setup
-------------------------------

Data, event file and the config file for Grond can be found here:

    https://owncloud.ifg.uni-kiel.de/index.php/s/6BNeW2k5AnVI44L


We will use a Greensfunction storage that you can obtain by:

    fomosto download kinherd global_2s_25km

You will have to adjust the path at the ending of the conf.yml called
gf_store_superdirs with a path where you downloaded this store.


Sources covered in these examples:
 * :py:mod:`pyrocko.moment_tensor` (a 3x3 matrix representation of an
   earthquake source)
 * :py:class:`pyrocko.gf.seismosizer.DCSource` (a representation of a double
   couple source object)


Optimzing from Command console
-------------------------------

Inside the unpacked folder you can start the optimization for the
Source of the L'Aquila 2009 earthquake, using only the P-waves with the
following command:

    grond <subcommand> [options]
    
    it will look this:
    
    grond go conf.yml 200904060132A

If there is a warning like:
    WARNING  - skipping problem cmt_%(event_name)s: rundir already exists: gruns/amatrice.run

This happens because there is already an exisiting folder, that contains a previously run optimization.

You have to change the rundir in the top most row of the config (rundir_template) or delete the folder
gruns or use the --force option:

    grond go conf.yml 200904060132A --force
    
This will overwrite the folder.


Optimzing from Script 
-------------------------------

Alternativly to the console version a script can be used:



::

    import math
    import os
    import os.path as op
    import sys
    import logging
    import time
    import copy
    import sys
    import numpy as num
    
    
    from pyrocko import gf, util
    from pyrocko.parimap import parimap
    
    import grond
    
    #import solverscipy
    
    km = 1000.
    rundir = 'gruns'
    
    #######################   provide data set  ###################################
    
    ## initialize and fill dataset object
    ds = grond.Dataset()  ## initialize Dataset
    ds.add_events(filename='event.csv')
    ds.add_stations(stationxml_filenames=['restfuncs.xml'])
    ds.add_responses(stationxml_filenames=['restfuncs.xml'])
    ds.add_waveforms(paths=['data'])
    
    ### exclude entire station recordings by black-listing them here
    #ds.add_blacklist([
     #   'PM.ROSA', 
    #])
    
    #For fast testing use this as blacklist:
    #ds.add_blacklist([
    #'PM.ROSA', 'KZ.AKTO', 'KZ.KKAR', 'IC.WMQ.10', 'TA.F13A', 'TA.A19A', 'CU.GTBY', 'CU.ANWB', 'CU.GRGR', 'PS.PSI', #'X4.F16', 'CB.GTA.00', 'IU.KMBO.10', 'XW.LUSA', 'GT.LBTB.00',
    #'IU.TSUM.10', 'II.MSEY.00', 'II.SACV.00', 'ZF.ADYE', 'II.ALE.10', 'CN.RES', 'IU.COLA.00', 'TA.232A', 'TA.A19A'])
    
    
    ds.empty_cache()
    
    #########################   configure  data    ################################
    ## Configure now the use of your data,
    ## which is the TargetConfiguration
    
    ## 1a) What quantity do you want to fit,
    ##                     'displacement',
    ##                     'velocity' or
    ##                     'accelaration',
    ##     and in which domain,
    ##                     'frequency_domain',
    ##                     'time_domain'? 
    ##     (for 'super_group' more option may be
    ##     available to define in 'group')
    quantity = 'displacement'
    super_group = 'time_domain'
    group = 'all'
    
    ## 2a) Set phases you want to fit, 'P' and/or 'S' (predicted arrival times must 
    ##     be included in the GF data base)
    ## 2b) Set corresponding filter values (default is Butterworth bandpass filter 
    ##     of order 4) and, 
    ## 2c) set corresponding time window of trace relative to phase arrival times  
    ## 2d) set also channels in which to fit the phase waveform
    imc_P = grond.InnerMisfitConfig(
        fmin=0.025,
        fmax=0.045,
        tmin='P-5',
        tmax='P+5')
    cha_P ='ZR'
    
    imc_S = grond.InnerMisfitConfig(
        fmin=0.025,
        fmax=0.045,
        tmin='S-5',
        tmax='S+5')
    cha_S ='ZT'
    
    ###########################    provide event   ################################
    ## 3) Get the corresponding event into the play by relating station configurations
    ##    to source region 
    ##    (internally relative distances between source and receivers are used).
    ##    Get rough event position (e.g. a GCMT estimate) and make location object
    ##    "event_origin" to be used later in the 
    event = ds.get_events()[0] 
    event_origin = gf.Source(
        lat=event.lat,
        lon=event.lon)
    
    ## 
    if event.depth is None:
        event.depth = 7*km
    
    # define distance minimum
    distance_min = None
    distance_max = None
    
    
    ########################### define medium store  ##############################
    ## 4) Define the medium model you want to use - here via choosing the 
    ##    precalculated Green's function store and the store path
    store_id = 'global_2s_25km'
    #os.environ["GF_STORE_SUPERDIRS"] = "/home/hsudhaus/python/gf_stores" 
    
    ##    set up the 'engine' to use the GF store in the modelling
    engine = gf.LocalEngine(store_superdirs=['your_path'])
    
    ##    Furthermore the interpolation of the discrete Green's functions is
    ##    defined ('nearest_neighbor' would be an option, too)
    gf_interpolation = 'multilinear'
    
    
    ######################  wrap up target configuration ##########################
    ## 5) Finish Configuring the target by bringing all information
    ##    defined above together
    targets = []
    ## first for P phases
    for st in ds.get_stations():
        for cha in cha_P:
            target = grond.MisfitTarget(
                quantity=quantity,
                super_group=super_group,
                group=group,
                codes=st.nsl() + (cha,),
                lat=st.lat,
                lon=st.lon,
                interpolation=gf_interpolation,
                store_id=store_id,
                misfit_config=imc_P)
            _, bazi = event_origin.azibazi_to(target)
            if cha == 'R':
                target.azimuth = bazi - 180.
                target.dip = 0.
            elif cha == 'T':
                target.azimuth = bazi - 90.
                target.dip = 0.
            elif cha == 'Z': 
                target.azimuth = 0.
                target.dip = -90.
            target.set_dataset(ds)
            targets.append(target)
    # for S phases
    for st in ds.get_stations():
        for cha in cha_S:
            target = grond.MisfitTarget(
                quantity=quantity,
                super_group=super_group,
                group=group,
                codes=st.nsl() + (cha,),
                lat=st.lat,
                lon=st.lon,
                interpolation=gf_interpolation,
                store_id=store_id,
                misfit_config=imc_S)
            _, bazi = event_origin.azibazi_to(target)
            if cha == 'R':
                target.azimuth = bazi - 180.
                target.dip = 0.
            elif cha == 'T':
                target.azimuth = bazi - 90.
                target.dip = 0.
            elif cha == 'Z': 
                target.azimuth = 0.
                target.dip = -90.
            target.set_dataset(ds)
            targets.append(target)
    
    
    ###################  define source  model #####################################
    ##  Source type: here we choose the source model - check for source options 
    ##  in the pyrocko manual - and define a center value for the source location.
    base_source = gf.MTSource.from_pyrocko_event(event)
    base_source.set_origin(event_origin.lat, event_origin.lon)
    
    ##  Here we set the optimization ranges for the source parameters
    ranges=dict(
        time=gf.Range(-20, 20.0, relative='add'),
        north_shift=gf.Range(-20*km, 20*km),
        east_shift=gf.Range(-20*km, 20*km),
        depth=gf.Range(1*km, 20*km),
        magnitude=gf.Range(6.2, 6.4),
        duration=gf.Range(5.,15.),
        rmnn=gf.Range(0., 0.45),
        rmee=gf.Range(0.25, 0.6),
        rmdd=gf.Range(-3.0, 1.),
        rmne=gf.Range(0.3, 1.0),
        rmnd=gf.Range(-0.5, -0.25),
        rmed=gf.Range(0.01, 0.15))
    
    
    ################# define the "problem"    #####################################
    
    ## The target positions and target configurations together with the source and
    ## and medium definitions define the "problem" we want to solve. Note: the 
    ## misfit configuration defines the 'objective function' here.
    
    problem = grond.problems.CMTProblem(
        name=event.name,
        apply_balancing_weights='True',
        base_source=base_source,
        distance_min=20.*km,
        nbootstrap=10,
        mt_type='deviatoric',
        ranges=ranges,
        targets=targets,
        )
    
    problem.set_engine(engine)
    
    ##  (...)
    grond.core.analyse(
        problem,
        niter=100,
        show_progress=False)
    
    problem.dump_problem_info(rundir)
    ####  Now we can solve the "problem". The solver is in principle a certain
    ##  sampler of the model space. At the moment there is the generic Grond-
    print 'start optimization'
    tstart = time.time()
    grond.core.solve(problem, 
                     rundir=rundir, 
                     niter_uniform=1000, 
                     niter_transition=40000,
                     niter_explorative=0,
                     sampler_distribution='uniform',
                     scatter_scale_transition=4.0)
    
    #solverscipy.solve(problem, quiet=False, niter_explorative=2000, niter=10000)
    tstop = time.time()
    print 'processing time '+str(tstart-tstop)

    
.. figure:: /static/aquila_beachballs.png
    :scale: 40%

    
    
Static optimization 
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Static optimization preparation
-------------------------------

Data, event file and the config file for Grond can be found here:

    <PLACEHOLDER>





We will use a Greensfunction storage that you will have to build 

    fomosto init psgrn_pscmp.2008a gf_abruzzo_nearfield_vmod_Ameri
    
now
    cd gf_abruzzo_nearfield_vmod_Ameri
    
and replace the content in the config file with the following information:

::


    --- !pf.ConfigTypeA
    id: italy
    modelling_code_id: psgrn_pscmp.2008a
    earthmodel_1d: |2
       0.             3.16           1.7           2.5  200.           100.
       1.             4.83           2.6           2.84 400.           200.
       2.             5.76           3.1           2.94 400.           200.
       5.             6.51           3.5           3.15 400.           200.
       27.            7.             3.8           3.26 600.           300.
       42.            7.8            4.2           3.50 800.           400.
    sample_rate: 1.0
    component_scheme: elastic10
    ncomponents: 10
    receiver_depth: 0.0
    source_depth_min: 50.0
    source_depth_max: 30000.0
    source_depth_delta: 500.0
    distance_min: 0.0
    distance_max: 450000.0
    distance_delta: 500.0




You will have to adjust the path at the ending of the conf.yml and or in your script the variable
called gf_store_superdirs with a path where you created this store.


Optimzing from Command console
-------------------------------



Optimzing from Script 
-------------------------------


::


    import math
    import os
    import os.path as op
    import sys
    import logging
    import time
    import copy
    import sys
    import numpy as num
    
    
    from pyrocko import gf, util
    from pyrocko.parimap import parimap
    
    import grond
    
    #import solverscipy
    
    km = 1000.
    rundir = 'gruns'
    
    #######################   provide data set  #################################
    
    
    ####1 ) InSAR scene preparation ####
     
    ## initialize and fill dataset object
    ds = grond.Dataset()  ## initialize Dataset
    ds.add_events(filename='event.csv')
    
    ds.add_kite_scene('scenes/asc')
    ds.add_kite_scene('scenes/dsc')
    
    
    ds.empty_cache()
    
    #########################   configure  data    ################################
    ## 2) Configure now the use of your data,
    ## which is the TargetConfiguration
    
    ## Define the orbital ramp that should be fitted:
    ranges_orbit_ramp=dict(
        ramp_east=gf.Range(-5e-4, 5e-4),
        ramp_north=gf.Range(-5e-4, 5e-4),
        offset=gf.Range(-0.5, 0.5))
        
    ## Define what you want to fit:       
    imc = grond.InnerSatelliteMisfitConfig(
        use_weight_focal= 'false',
        optimize_orbital_ramp= 'true', #True or false for optimizing the ramps for each scene 
        ranges=ranges_orbit_ramp)
    
    
    
    ###########################    provide event   ################################
    ## 3) Get the corresponding event into the play by relating station configurations
    ##    to source region 
    ##    (internally relative distances between source and receivers are used).
    ##    Get rough event position (e.g. a GCMT estimate) and make location object
    ##    "event_origin" to be used later in the 
    event = ds.get_events()[0] 
    event_origin = gf.Source(
        lat=event.lat,
        lon=event.lon)
    
    
    ########################### define medium store  ##############################
    ## 4) Define the medium model you want to use - here via choosing the 
    ##    precalculated Green's function store and the store path
    store_id = 'gf_abruzzo_nearfield_vmod_Ameri'
    os.environ["GF_STORE_SUPERDIRS"] = "/media/asteinbe/data/asteinbe/aragorn/andreas/Tibet" 
    
    ##    set up the 'engine' to use the GF store in the modelling
    engine = gf.LocalEngine(store_superdirs=['your_path'])
    
    ##    Furthermore the interpolation of the discrete Green's functions is
    ##    defined ('nearest_neighbor' would be an option, too)
    gf_interpolation = 'multilinear'
    
    
    ######################  wrap up target configuration ##########################
    ## 5) Finish Configuring the target by bringing all information
    ##    defined above together
    
    
    ###################  define source  model #####################################
    ##  Source type: here we choose the source model - check for source options 
    ##  in the pyrocko manual - and define a center value for the source location.
    base_source = gf.RectangularSource.from_pyrocko_event(event)
    base_source.set_origin(event_origin.lat, event_origin.lon)
    
    ##  Here we set the optimization ranges for the source parameters
    ranges=dict(
        length=gf.Range(2*km, 9*km),
        width=gf.Range(2*km, 5*km),
        north_shift=gf.Range(-10*km, 10*km),
        east_shift=gf.Range(-10*km, 10*km),
        depth=gf.Range(2.5*km, 10*km),
        rake=gf.Range(0.,90.),
        strike=gf.Range(0.,180.),
        dip=gf.Range(20.,70.),
        slip=gf.Range(1,3.))
    
    
    ################# define the "problem"    #####################################
    
    ## The target positions and target configurations together with the source and
    ## and medium definitions define the "problem" we want to solve. Note: the 
    ## misfit configuration defines the 'objective function' here.
    
    targets=[]
    for scene in ds.get_kite_scenes():
        qt = scene.quadtree
    
        lats = num.empty(qt.nleafs)
        lons = num.empty(qt.nleafs)
        lats.fill(qt.frame.llLat)
        lons.fill(qt.frame.llLon)
    
        east_shifts = qt.leaf_focal_points[:, 0]
        north_shifts = qt.leaf_focal_points[:, 1]
    
        sat_target = grond.MisfitSatelliteTarget(
            quantity='displacement',
            scene_id=scene.meta.scene_id,
            lats=lats,
            lons=lons,
            east_shifts=east_shifts,
            north_shifts=north_shifts,
            theta=qt.leaf_thetas,
            phi=qt.leaf_phis,
            tsnapshot=None,
            interpolation=gf_interpolation,
            store_id=store_id,
            super_group=super_group,
            group=group,
            inner_misfit_config=imc)
    
        sat_target.set_dataset(ds)
        targets.append(sat_target)
                
                
    problem = grond.problems.RectangularProblem(
        name=event.name,
        apply_balancing_weights='False',
        base_source=base_source,
        ranges=ranges,
        targets=targets,
        )
    
    problem.set_engine(engine)
    
    ##  (...)
    grond.core.analyse(
        problem,
        niter=100,
        show_progress=False)
    
    problem.dump_problem_info(rundir)
    
    
    ####  Now we can solve the "problem". The solver is in principle a certain
    ##  sampler of the model space. At the moment there is the generic Grond-
    print 'start optimization'
    tstart = time.time()
    grond.core.solve(problem, 
                     rundir=rundir, 
                     niter_uniform=1000, 
                     niter_transition=40000,
                     niter_explorative=0,
                     sampler_distribution='uniform',
                     scatter_scale_transition=4.0,
             status='state')
    
    #solverscipy.solve(problem, quiet=False, niter_explorative=2000, niter=10000)
    tstop = time.time()
    print 'processing time '+str(tstart-tstop)




