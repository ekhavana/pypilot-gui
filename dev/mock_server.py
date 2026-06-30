#!/usr/bin/env python
# Mock pypilot backend for developing/testing the web GUI without hardware.
# Emits the same socket.io protocol as pypilot's web.py but simulates an
# autopilot, so you can run the GUI on any desktop.  Open http://localhost:8000
import json
import math
import os
import time

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from markupsafe import Markup

PORT = 8000
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__,
            template_folder=os.path.join(_ROOT, 'templates'),
            static_folder=os.path.join(_ROOT, 'static'))
app.config['SECRET_KEY'] = 'mock'
socketio = SocketIO(app, cors_allowed_origins='*')
app.jinja_env.globals['_'] = lambda s: s

LIST_VALUES = {
    'ap.enabled': {'type': 'BooleanProperty'},
    'ap.mode': {'type': 'EnumProperty', 'choices': ['compass', 'gps', 'wind', 'true wind']},
    'ap.modes': {'type': 'Property'},
    'ap.heading': {'type': 'SensorValue'},
    'ap.heading_command': {'type': 'RangeProperty', 'min': 0, 'max': 360},
    'ap.pilot': {'type': 'EnumProperty', 'choices': ['basic', 'simple', 'wind']},
    'ap.tack.state': {'type': 'EnumProperty'},
    'ap.tack.timeout': {'type': 'SensorValue'},
    'ap.runtime': {'type': 'Value'},
    'ap.version': {'type': 'Value'},
    'profile': {'type': 'Property'},
    'profiles': {'type': 'Property'},
    'rudder.source': {'type': 'Value'},
    'rudder.angle': {'type': 'SensorValue'},
    'rudder.range': {'type': 'RangeProperty', 'min': 10, 'max': 100},
    'imu.heading': {'type': 'SensorValue'},
    'imu.pitch': {'type': 'SensorValue'},
    'imu.roll': {'type': 'SensorValue'},
    'imu.heading_offset': {'type': 'RangeProperty', 'min': -180, 'max': 180},
    'imu.compass.calibration.locked': {'type': 'BooleanProperty'},
    'imu.accel.calibration.locked': {'type': 'BooleanProperty'},
    'servo.amp_hours': {'type': 'SensorValue'},
    'servo.voltage': {'type': 'SensorValue'},
    'servo.controller_temp': {'type': 'SensorValue'},
    'servo.engaged': {'type': 'BooleanProperty'},
    'servo.flags': {'type': 'Value'},
    'servo.controller': {'type': 'Value'},
    'imu.error': {'type': 'Value'},
    'imu.warning': {'type': 'Value'},
    'nmea.client': {'type': 'Property'},
    'signalk.host': {'type': 'Property'},
    # gains for two pilots
    'ap.pilot.basic.P': {'AutopilotGain': True, 'min': 0, 'max': 0.05},
    'ap.pilot.basic.I': {'AutopilotGain': True, 'min': 0, 'max': 0.05},
    'ap.pilot.basic.D': {'AutopilotGain': True, 'min': 0, 'max': 0.5},
    'ap.pilot.simple.P': {'AutopilotGain': True, 'min': 0, 'max': 0.05},
    'ap.pilot.simple.D': {'AutopilotGain': True, 'min': 0, 'max': 0.5},
    # config range settings
    'ap.max_current': {'type': 'RangeSetting', 'min': 0, 'max': 60, 'units': 'A', 'profiled': False},
    'servo.period': {'type': 'RangeSetting', 'min': 0.1, 'max': 3, 'units': 's', 'profiled': False},
    'ap.gps_compass_offset': {'type': 'RangeSetting', 'min': -180, 'max': 180, 'units': 'deg', 'profiled': True},
}

state = {
    'ap.enabled': False,
    'ap.mode': 'compass',
    'ap.modes': ['compass', 'gps', 'wind', 'true wind'],
    'ap.heading': 142.0,
    'ap.heading_command': 150.0,
    'ap.pilot': 'basic',
    'ap.tack.state': 'none',
    'ap.tack.timeout': 0,
    'ap.runtime': '0:12:33',
    'ap.version': 'mock-1.0',
    'profile': 'default',
    'profiles': ['default', 'rough'],
    'rudder.source': 'servo',
    'rudder.angle': 0.0,
    'rudder.range': 30,
    'imu.heading': 142.0,
    'imu.pitch': 1.2,
    'imu.roll': -0.4,
    'imu.heading_offset': 0,
    'imu.compass.calibration.locked': False,
    'imu.accel.calibration.locked': False,
    'servo.amp_hours': 0.123,
    'servo.voltage': 12.6,
    'servo.controller_temp': 31,
    'servo.engaged': False,
    'servo.flags': 'PORT_FAULT 0',
    'servo.controller': 'arduino',
    'imu.error': '',
    'imu.warning': '',
    'nmea.client': '',
    'signalk.host': '',
    'ap.pilot.basic.P': 0.003, 'ap.pilot.basic.I': 0.0, 'ap.pilot.basic.D': 0.09,
    'ap.pilot.simple.P': 0.004, 'ap.pilot.simple.D': 0.10,
    'ap.max_current': 20, 'servo.period': 0.4, 'ap.gps_compass_offset': 0,
}

watches = {}
clients = {}   # sid -> bool (value list already sent)


@app.route('/')
def index():
    return render_template('index.html', pypilot_web_port=PORT, tinypilot=0,
                           translations=[], language='default', languages=Markup('[]'))


@socketio.on('connect')
def on_connect():
    from flask import request
    clients[request.sid] = False


@socketio.on('disconnect')
def on_disconnect():
    from flask import request
    clients.pop(request.sid, None)


@socketio.on('ping')
def on_ping():
    emit('pong')


@socketio.on('language')
def on_language(_lang):
    pass


@socketio.on('pypilot')
def on_pypilot(msg):
    if msg.startswith('watch='):
        w = json.loads(msg[6:])
        for k, v in w.items():
            watches[k] = v
        # immediately echo current values being watched
        emit('pypilot', json.dumps({k: state[k] for k in w if k in state}))
        return
    i = msg.find('=')
    name, val = msg[:i], json.loads(msg[i + 1:])
    state[name] = val
    if name == 'ap.enabled':
        state['servo.engaged'] = val
    emit('pypilot', json.dumps({name: val}))


def sim_loop():
    tick = 0
    while True:
        socketio.sleep(0.25)
        tick += 1
        # mimic web.py: send the value list ONCE per client, then snapshot
        for sid in list(clients):
            if not clients.get(sid):
                socketio.emit('pypilot_values', json.dumps(LIST_VALUES), room=sid)
                socketio.emit('pypilot', json.dumps(state), room=sid)
                clients[sid] = True
        if state['ap.enabled']:
            err = state['ap.heading_command'] - state['ap.heading']
            state['ap.heading'] += max(-2, min(2, err * 0.25))
            state['rudder.angle'] = round(max(-30, min(30, err)), 1)
        else:
            state['ap.heading'] += 0.4 * math.sin(time.time() / 3.0)
        state['ap.heading'] = round(state['ap.heading'] % 360, 1)
        state['imu.heading'] = state['ap.heading']
        state['servo.amp_hours'] = round(state['servo.amp_hours'] + 0.0001, 4)
        upd = {k: state[k] for k in ('ap.heading', 'imu.heading', 'rudder.angle', 'servo.amp_hours')}
        socketio.emit('pypilot', json.dumps(upd))


if __name__ == '__main__':
    print('pypilot-gui mock server: http://localhost:%d' % PORT)
    socketio.start_background_task(sim_loop)
    socketio.run(app, host='0.0.0.0', port=PORT)
