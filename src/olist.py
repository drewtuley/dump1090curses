from PyRadar import ObservationDetail
from PyRadar import PyRadar

if __name__ == "__main__":

    pyradar = PyRadar()
    pyradar.set_config("config.toml")
    pyradar.set_logger(pyradar.config["directories"]["log"] + "/olist.log")

    session = pyradar.get_db_session()
    obvs = session.query(ObservationDetail).filter(
        ObservationDetail.event_time > "2019-03-20"
    )
    for obv in obvs:
        print(obv)
