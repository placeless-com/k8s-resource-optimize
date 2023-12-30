import time

import pandas as pd
# import placelessdb
# from
import copy
class Pnode:

    def __init__(self, id: tuple, request=()):

        self.__id = id
        self.__cpu_model = None
        self.__memory_model = None

    @property
    def cpu_model(self):
        return self.__cpu_model
    @property
    def memory_model(self):
        return self.__memory_model

    def get_id(self):
        id = copy.deepcopy(self.__id)
        return id


    def set_cpu_model(self,model):
        self.__cpu_model = model

    def set_memory_model(self, model):
        self.__memory_model = model

    def set_id(self, id):
        self.__id = id


