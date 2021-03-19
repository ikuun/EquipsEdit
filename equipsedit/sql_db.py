import pymysql

class Connector(object):
    """
        Python与Mysql连接器
    """
    def __init__(self, host, port, user, pwd, db):
        conn = pymysql.connect(host=host, port=port, user=user,
                                passwd=pwd, db=db, use_unicode=True, charset="utf8")

        self.conn = conn
        self.cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    def execute(self, sql: str):
        '''
        执行sql语句
        :param str sql: sql语句
        :return:
        '''
        ret = self.cursor.execute(sql)
        self.conn.commit()
        return ret

    def close(self):
        '''
        关闭数据库连接
        :return:
        '''

        self.cursor.close()
        self.conn.close()