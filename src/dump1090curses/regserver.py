import json
import os
import tomllib
from datetime import datetime

from flask import Flask, request, Blueprint, current_app, jsonify
from sqlalchemy import text

from PyRadar import Location, PyRadar, Registration, PlaneOfInterest, ObservationLog


class RegServer(Flask):
    logger = None

    def set_db(self, filename):
        self.db_filename = filename

    def set_pyradar(self, pyradar):
        self.pyradar = pyradar

    def set_logger(self, logger):
        self.logger = logger


health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health():
    app = current_app

    # Basic structural checks
    if not getattr(app, "pyradar", None):
        app.logger.error("health: pyradar missing")
        return jsonify(status="fail", detail="pyradar missing"), 503

    # Check DB connectivity with a lightweight query
    try:
        session = app.pyradar.get_db_session()
        # lightweight query; SQLAlchemy 1.4+ supports text()
        session.execute(text("SELECT 1"))
    except Exception as e:
        app.logger.exception("health: DB check failed")
        return jsonify(status="fail", detail="db error"), 503
    finally:
        try:
            session.close()
        except Exception:
            pass

    try:
        # ensure log dir exists and is writable
        logdir = app.pyradar.config["directories"]["log"]
        open(f"{logdir}/.healthwrite", "w").close()
        os.remove(f"{logdir}/.healthwrite")
    except Exception:
        app.logger.exception("health: log dir not writable")
        return jsonify(status="fail", detail="logdir not writable"), 503

    return jsonify(status="ok"), 200


places_bp = Blueprint("places", __name__)


@places_bp.route("/places", methods=["GET"])
def places():
    app = current_app
    session = app.pyradar.get_db_session()
    locs = session.query(Location)
    ret = {}
    for loc in locs:
        ret[loc.name] = (loc.latitude, loc.longitude)
    return json.dumps(ret)


pois_bp = Blueprint("pois", __name__)


@pois_bp.route("/pois", methods=["GET"])
def pois():
    app = current_app
    session = app.pyradar.get_db_session()
    pois = session.query(PlaneOfInterest)
    ret = []
    for poi in pois:
        ret.append(poi.callsign)
    return json.dumps(ret)


search_bp = Blueprint("search", __name__)


@search_bp.route("/search", methods=["GET"])
def search():
    app = current_app
    search_icao_code = request.args.get("icao_code", "").upper()
    app.logger.info("search for {}".format(search_icao_code))
    ret = {}
    session = app.pyradar.get_new_db_session()
    reg = session.query(Registration).filter_by(icao_code=search_icao_code).first()
    app.logger.debug(
        "loaded reg {0} from DB for icao {1}".format(reg, search_icao_code)
    )
    if reg is not None:
        ret = {"registration": reg.registration, "equip": reg.equip}

        log = ObservationLog()
        log.log_event(search_icao_code, str(datetime.now()))
        session.add(log)
        session.commit()

    else:
        app.logger.debug("not in db")

    return json.dumps(ret)


def create_app(config_path="config.toml"):
    app = RegServer(__name__)
    with open(config_path, "rb") as cf:
        config = tomllib.load(cf)

    app.register_blueprint(places_bp)
    app.register_blueprint(pois_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(health_bp)

    pyradar = PyRadar()
    pyradar.set_config(config_path)
    pyradar.set_logger(pyradar.config["directories"]["log"] + "/regserver.log")
    app.set_pyradar(pyradar)
    app.set_logger(pyradar.logger)
    app.logger.info("started")
    for rule in app.url_map.iter_rules():
        app.logger.info("ROUTE %s %s", rule.endpoint, rule.rule)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5001)
