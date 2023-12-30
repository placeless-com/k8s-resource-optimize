from placelessdb import usage_table, workload_table, FT_Groups, residual_table, prediction_table, event_table, \
    updates_table
from placelessdb.common import open_connection, get_conn_params


class PDB:
    '''
    if PDB is executed in OSS, PDB requires DB auth details
    else PDB connected to SAAS DB
    @return DB connection
    '''

    def __init__(self, db_host=None,
                 db_user=None,
                 db_pass=None,
                 db_name=None):
        if db_host:
            self.connection = open_connection([db_host, db_user, db_pass, db_name])
        else:
            self.connection = open_connection(get_conn_params())

    @property
    def WorkloadUsagAvg(self):
        return usage_table.WorkloadUsagAvg(self.connection)

    @property
    def Residuals(self):
        return residual_table.Residuals(self.connection)

    @property
    def Workload(self):
        return workload_table.Workload(self.connection)

    @property
    def FT(self):
        return FT_Groups.Groups(self.connection)

    @property
    def Predictions(self):
        return prediction_table.Prdiction(self.connection)

    @property
    def events(self):
        return event_table.Event(self.connection)

    @property
    def Updates(self):
        return updates_table.Update(self.connection)
