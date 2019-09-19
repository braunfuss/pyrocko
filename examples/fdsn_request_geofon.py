from pyrocko.client import fdsn
from pyrocko import util, io, trace, model
from pyrocko.io import quakeml

tmin = util.stt('2014-01-01 16:10:00.000')
tmax = util.stt('2014-01-01 16:39:59.000')

# request events at IRIS for the given time span
request_event = fdsn.event(
    site='iris', starttime=tmin, endtime=tmax)

# parse QuakeML and extract pyrocko events
events = quakeml.QuakeML.load_xml(request_event).get_pyrocko_events()
model.dump_events(events, 'iris-events.pf')


# select stations by their NSLC id and wildcards (asterisk) for waveform
# download
selection = [
    ('*', 'HMDT', '*', '*', tmin, tmax),    # all available components
    ('GE', 'EIL', '*', '*Z', tmin, tmax),   # all vertical components
]

# Restricted access token
# token = open('token.asc', 'rb').read()
# request_waveform = fdsn.dataselect(site='geofon', selection=selection,
#                                    token=token)

# setup a waveform data request
request_waveform = fdsn.dataselect(site='geofon', selection=selection)

# write the incoming data stream to 'traces.mseed'
with open('traces.mseed', 'wb') as file:
    file.write(request_waveform.read())

# request meta data
request_response = fdsn.station(
    site='geofon', selection=selection, level='response')

# save the response in YAML and StationXML format
request_response.dump(filename='responses_geofon.yaml')
request_response.dump_xml(filename='responses_geofon.xml')

# Loop through retrieved waveforms and request meta information
# for each trace
traces = io.load('traces.mseed')
displacement = []
for tr in traces:
    polezero_response = request_response.get_pyrocko_response(
        nslc=tr.nslc_id,
        timespan=(tr.tmin, tr.tmax),
        fake_input_units='M')
    # *fake_input_units*: required for consistent responses throughout entire
    # data set

    # deconvolve transfer function
    restituted = tr.transfer(
        tfade=2.,
        freqlimits=(0.01, 0.1, 1., 2.),
        transfer_function=polezero_response,
        invert=True)

    displacement.append(restituted)

# Inspect waveforms using Snuffler
trace.snuffle(displacement)
