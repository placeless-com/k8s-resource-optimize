from placelessdb.common import insert_table

class Groups():
    def __init__(self, db_obj):
        self.conn = db_obj
        self.cur = db_obj.cursor()


    def insert(self, FT, cost, name):
        insert_table(self.conn,'FT_Groups', ('FT', 'costH', 'Gname'), (FT,  cost, name))

    def delete(self, FT):
        query = "DELETE FROM 'Groups' WHERE 'FT' = {}".format(FT)
        self.cur.execute(query)
        self.conn.commit()
