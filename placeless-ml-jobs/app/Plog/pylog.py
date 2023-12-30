import logging

class PlaceLog:
    def __init__(self, dbname=None):
       self.db = dbname


    # problem alert E.g time passed without insertion, nulls ...
    def debug(self, massage: str):
        logging.basicConfig(filename='Log', level=logging.DEBUG)
        logging.debug(massage)

    # things going as expected E.g well insertion to DB, usage prediction is on track...
    def info(self,massage):
        logging.basicConfig(filename='Log', level=logging.INFO)
        logging.info(massage)

    # indication that there is a potential problem on the way E.g usage prediction is not on track...
    def warning(self,massage):
        logging.basicConfig(filename='Log', level=logging.WARNING)
        logging.warning(massage)

    # error in production E.g some function returns an error\Exception....
    def error(self, massage):
        logging.basicConfig(filename='Log', level=logging.ERROR)
        logging.error(massage)





