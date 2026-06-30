# pypilot-gui

A redesigned, touch-optimized web GUI for [pypilot](https://github.com/pypilot/pypilot),
the open-source marine autopilot. Built for use on a boat: dark / sunlight-readable
theme, large touch targets, and a lightweight vanilla-JS frontend that runs well on a
Raspberry Pi Zero 2 W (tinypilot).

It is a **drop-in replacement** for pypilot's stock web interface — it speaks the exact
same socket.io protocol, so it needs **no protocol/autopilot changes**. The calibration
plot and the full settings browser are embedded directly in the GUI. Embedding the WiFi
config (tinypilot) additionally uses a small, optional tweak to `web.py`'s `index()` route
(see Install) to prefill the form; without it the form still works, just unprefilled.

## What's here

```
templates/index.html          new GUI page (Jinja template, served by pypilot's web.py)
static/pypilot_app.css         styles (dark default + light theme)
static/pypilot_app.js          app logic + canvas compass, vanilla JS
static/pypilot_calplot.js      WebGL calibration plot (embedded), vanilla JS
static/socket.io.min.js        socket.io client (same version pypilot ships)
dev/mock_server.py             simulated autopilot for local dev/testing (no hardware)
```

## Features

- Big central heading + command readout with a canvas compass rose
- Large port/starboard steering buttons and a prominent ENGAGE / STANDBY toggle
- Mode selector (compass / gps / wind / true wind) and Tack
- Control / Gain / Calibration / Configuration / Statistics tabs (feature parity with the classic UI)
- Dark, high-contrast, sunlight-readable theme + light toggle
- Embedded WebGL calibration plot (accel/compass 3D sphere) in the Calibration tab
- Embedded "Advanced" editor in Configuration: every pypilot value with the right control
  (range / checkbox / enum / reset / read-only), live updates and a name filter
- Embedded WiFi config (tinypilot only): Master / Managed / Master+Managed, saved via /wifi
- No CDN / no internet required, no jQuery or frameworks

## Install onto a pypilot / tinypilot machine

Copy the files into your pypilot `web/` folder (back up the originals first):

```sh
# on the Pi, with this repo checked out or copied over:
cp templates/index.html   <pypilot>/web/templates/index.html
cp static/pypilot_app.css      <pypilot>/web/static/
cp static/pypilot_app.js       <pypilot>/web/static/
cp static/pypilot_calplot.js   <pypilot>/web/static/
# socket.io.min.js already ships with pypilot; only copy if missing
```

Then restart the web service (`pypilot_web`). The old GUI remains available at `/classic`
if you also keep the original `index.html` as `templates/classic.html`.

### Optional: embedded WiFi prefill (tinypilot)

To prefill the embedded WiFi form (and show DHCP leases) from `~/.pypilot/networking.txt`,
have `web.py`'s `index()` pass the current config to the template:

```python
@app.route('/')
def index():
    wifi = read_wifi() if tinypilot.tinypilot else {}
    return render_template('index.html', ...,  # existing args
                           wifi=Markup(pyjson.dumps(wifi)),
                           wifi_leases=Markup(wifi_leases(wifi) if tinypilot.tinypilot else ''))
```

where `read_wifi()` / `wifi_leases()` are the helpers factored out of the existing `/wifi`
route. Without this change the form still submits correctly to `/wifi`; it just starts blank.

## Local development / testing (no autopilot hardware)

The mock server simulates an autopilot speaking pypilot's protocol so you can preview the
GUI on any desktop:

```sh
pip install -r dev/requirements.txt
python dev/mock_server.py
# open http://localhost:8000
```

When ENGAGED, the simulated heading converges to the command; steering, gains, modes,
profiles and the tabs all round-trip against the mock.

## License

GPL-3.0-or-later, matching pypilot.
