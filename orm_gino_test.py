#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymysql

'''
本文件是基于mysql实现的一个ORM框架
'''

class MysqlConnector(object):
    '''Python与mysql的连接器'''

    def __init__(self, host, port, username, password, db):
        conn = pymysql.connect(host=host, port=port, user=username,
                               passwd=password, db=db, use_unicode=True, charset="utf8")
        self.conn = conn
        self.cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    def execute(self, sql_msg):
        '''
        执行sql语句
        :param sql_msg:  sql语句，字符串格式
        :return:
        '''
        ret = self.cursor.execute(sql_msg)
        self.conn.commit()
        return ret

    def close(self):
        '''关闭连接器'''
        self.cursor.close()
        self.conn.close()

class BaseModel(object):
    '''
    实现将Python语句转换为sql语句，配合MysqlConnector实现表的创建以及数据的增删查改等操作。
    创建表时： 支持主键PRIMARY KEY，索引INDEX，唯一索引UNIQUE，自增AUTO INCREMENT 外键语句
        创建的表引擎指定为InnoDB，字符集为 utf-8
    增删查改： 支持WHERE [LIKE] LIMIT语句
    其子类必须设置initialize方法，并在该方法中创建字段对象
    '''
    def __new__(cls, *args, **kwargs):
        _instance = super().__new__(cls)
        _instance.initialize()
        return _instance

    def __init__(self, table_name, sql_connector):
        '''
        :param table_name: 要建立的表名
        :param sql_connector: MysqlConnector实例对象
        '''
        self.table_name = table_name
        self.fields = []
        self.primary_key_field = None
        self.uniques_fields = []
        self.index_fields = []
        self.is_foreign_key_fields = []
        self.sql_connector = sql_connector
        self._create_fields_list()
        self.create_table()

    def initialize(self):
        '''BaseModel的每个子类中必需包含该方法，且在该方法中定义字段'''
        # raise NotImplementedError("Method or function hasn't been implemented yet.")

    def _create_fields_list(self):
        '''创建list用来存储表的字段对象'''
        t = self.__dict__
        for k, v in self.__dict__.items():
            if isinstance(v, BaseField):
                self.fields.append(v)
                v.full_column = '%s.%s' % (self.table_name, v.db_column)
                v.table_name = self.table_name
        for field in self.fields:
            if field.primary_key:
                self.primary_key_field = field
            if field.unique:
                self.uniques_fields.append(field)
            if field.db_index:
                self.index_fields.append(field)
            if field.is_foreign_key:
                self.is_foreign_key_fields.append(field)

    def _has_created(self):
        '''检测表有没有被创建'''
        self.sql_connector.cursor.execute('SHOW TABLES;')
        ret = self.sql_connector.cursor.fetchall()
        for table in ret:
            for k, v in table.items():
                if v == self.table_name:
                    return True

    def _create_table(self):
        ret = 'CREATE TABLE %s (' % self.table_name
        for v in self.fields:
            ret += v.generate_field_sql()
        ret = '%s%s%s%s%s' % (ret, self._generate_primary_key(),
                             self._generate_unique(), self._generate_index(),
                             self._generate_is_foreign_key())
        ret = ret[:-1] + ')ENGINE=InnoDB DEFAULT CHARSET=utf8;'
        return ret

    def create_table(self):
        '''创建表'''
        if not self._has_created():
            print('创建表：%s' % self.table_name)
            sql_msg = self._create_table()
            # print(sql_msg)
            self.sql_connector.execute(sql_msg)

    def _generate_primary_key(self):
        '''生成sql语句中的 primary key 语句'''
        ret = ''
        if self.primary_key_field:
            ret = 'PRIMARY KEY(%s),' % self.primary_key_field.db_column
        return ret

    def _generate_is_foreign_key(self):
        ret = ''
        if self.is_foreign_key_fields:
            for field in self.is_foreign_key_fields:
                ret += 'FOREIGN KEY(%s) REFERENCES %s(%s) ON DELETE %s  ON UPDATE %s,' % (field.db_column,
                                                  field.model_obj.table_name,
                                                  field.model_obj.primary_key_field.db_column,
                                                  field.on_delete,
                                                  field.on_delete )
        return ret

    def _generate_unique(self):
        '''生成sql语句中的 unique 语句'''
        ret = ''
        if self.uniques_fields:
            ret = 'UNIQUE ('
            for field in self.uniques_fields:
                ret += '%s,' % field.db_column
            ret = ret[:-1]
            ret += '),'
        return ret

    def _generate_index(self):
        index = ''
        if self.index_fields:
            index = 'INDEX ('
            for field in self.index_fields:
                index += '%s,' % field.db_column
            index = index[:-1]
            index += '),'
        return index

    def _generate_where(self, condition={}):
        '''
        根据条件生成 where 语句
        :param condition: 一个dict，key是字段对象，value是条件(比如 'WHERE ID=3',那么value就是'=3')
        :return:
        '''
        where = ''
        if condition:
            where = ' WHERE '
            for k, v in condition.items():
                v = v.strip()
                offset = 1
                if v.startswith('l'):
                    offset = 4
                if not k.is_str:
                    where += '%s %s and' % (k.db_column, v)
                else:
                    where += '%s %s "%s" and' % (k.db_column, v[:offset], v[offset:].strip())
            where = where[:-3]
        return where

    def select_items(self, counts=0, select_fields=[], condition={}, join_conditions=[]):
        '''
        根据condition 对表进行select，并 LIMIT counts
        :param counts:
        :param condition:
        :return:
        '''
        join_length = len(join_conditions)
        counts_sql = ''
        join_sql = ''
        select_fields_sql = ''
        where = self._generate_where(condition)
        if counts:
            counts_sql = 'LIMIT %s' % counts
        if not select_fields:
            select_fields_sql = '* '
        if join_conditions:
            tables_order = list(list(zip(*join_conditions))[0])
            tables_order.insert(0, self)
            for i in select_fields:
                select_fields_sql += '%s,' % i.full_column
            for n in range(join_length):
                one_join_condition = join_conditions[n]
                if n == 0:
                    base_table = tables_order[0].table_name
                else:
                    base_table = ''
                bracket_counts = join_length - n - 1
                join_sql += '%s %s LEFT JOIN %s on %s=%s%s' % (
                    bracket_counts*'(', base_table, tables_order[n+1].table_name,
                    one_join_condition[1].full_column, one_join_condition[2].full_column,
                    bracket_counts * ')', )
        else:
            for i in select_fields:
                select_fields_sql += '%s,' % i.db_column
            join_sql = self.table_name
        select_fields_sql = select_fields_sql[:-1]
        select = 'SELECT %s FROM %s %s %s;' % (select_fields_sql, join_sql, where, counts_sql)
        # print('----------------', select)
        self.sql_connector.execute(select)
        result = self.sql_connector.cursor.fetchall()
        return result

    def insert_item(self, data={}):
        '''
        向表中插入一行
        :param data: 一个dict，key是字段对象，value则是值
        :return:
        '''
        insert = 'INSERT INTO %s (' % self.table_name
        value = '('
        if data:
            for k, v in data.items():
                insert += '%s,' % k.db_column
                if k.is_str:
                    value += '"%s",' % v
                else:
                    value += '%s,' % v
                # print('value is ',value)
            insert = insert[:-1] + ')  VALUES '
            value = value[:-1] + ');'
            insert += value
        # print('......',insert)
        self.sql_connector.execute(insert)

    def delete_item(self, condition={}):
        '''删除符合condition的条目'''
        delete = 'DELETE FROM %s ' % self.table_name
        where = self._generate_where(condition)
        delete += where
        # print(delete)
        self.sql_connector.execute(delete)

    def update_item(self, data={}, condition={}):
        '''将符合condition的条目修改为data'''
        update = 'UPDATE %s' % self.table_name
        data_statement = ''
        if data:
            data_statement = ' SET '
            for k, v in data.items():
                if not k.is_str:
                    data_statement += '%s=%s,' % (k.db_column, v)
                else:
                    data_statement += '%s="%s",' % (k.db_column, v)
            data_statement = data_statement[:-1]
        where = self._generate_where(condition)
        update += data_statement + where
        # print('---------',update)
        self.sql_connector.execute(update)

    def get_field_value(self, field, condition={}):
        ret = self.select_items(condition=condition)
        # print(ret)
        if len(ret) == 1:
            value = ret[0][field.db_column]
        elif len(ret) > 1:
            value = []
            for i in ret:
                value.append(i[field.db_column])
        else:
            value = ''
        # print('value is ',value)
        return value

class BaseField(object):
    def __init__(self, db_column, null=True, blank=None, choice={},
                 db_index=False, default=None, primary_key=False,
                 unique=False, max_length=0, auto_increment=False,
                 ):
        '''

        :param db_column:  数据库中表的字段名
        :param null:  该字段是否可以为空
        :param blank: 如果该字段为空，存储什么值
        :param choice: 该字段的值只能是choice的一个
        :param db_index: 是否为该字段设置索引
        :param default: 该字段的默认值
        :param primary_key: 是否为该字段设置主键
        :param unique: 该字段值是否可以重复
        :param max_length： 该字段的最大长度
        :param auto_increment: 是否自增
        '''
        self.db_column = db_column
        self.null = null
        self.blank = blank
        self.choice = choice
        self.db_index = db_index
        self.default = default
        self.primary_key = primary_key
        if self.primary_key:
            self.null = False
        self.unique = unique
        self.max_length = max_length
        self.auto_increment = auto_increment
        self.is_foreign_key = False

    def generate_field_sql(self):
        pass

    def _generate_null(self):
        if not self.null:
            null = 'NOT NULL'
        else:
            null = 'NULL'
        return null

    def _generate_default(self):
        default = ''
        if self.default is not None:
            if self.is_str:
                default = ' DEFAULT "%s"' % self.default
            else:
                default = ' DEFAULT %s' % self.default
        return default

    def _generate_auto_increment(self):
        ret = ''
        if self.auto_increment:
            ret = 'AUTO_INCREMENT'
        return ret

class CharField(BaseField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        kwargs['blank'] = ''
        if not self.max_length:
            self.max_length = 128
        if not self.default:
            self.default = self.blank
        self.is_str = True
        self.field_type = 'CHAR'

    def generate_field_sql(self):
        null = self._generate_null()
        default = self._generate_default()
        return '%s CHAR(%s) %s %s,' % (self.db_column, self.max_length, null, default)

class IntField(BaseField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_str = False
        self.field_type = 'INT'

    def generate_field_sql(self):
        null = self._generate_null()
        default = self._generate_default()
        auto_increment = self._generate_auto_increment()
        return '%s INT %s %s %s,' % (self.db_column, null, default, auto_increment)

class ForeignKeyField(BaseField):
    def __init__(self, db_column, model_obj, null=True, default=None, on_delete='CASCADE'):
        self.db_column = db_column
        self.model_obj = model_obj
        self.null = null
        self.default = default
        self.is_str = model_obj.primary_key_field.is_str
        self.reference = model_obj.primary_key_field
        self.on_delete = on_delete
        self.is_foreign_key = True
        self.primary_key = False
        self.unique = False
        self.db_index = False

    def generate_field_sql(self):
        null = self._generate_null()
        default = self._generate_default()
        return '%s %s %s %s,' % (self.db_column, self.model_obj.primary_key_field.field_type, null, default)

Connector = MysqlConnector('127.0.0.1', 3306, 'root', 'admin', 'equipsedit')


if __name__ == '__main__':
    class UserModel(BaseModel):
        def initialize(self):
            self.uid = IntField('uid', primary_key=True, auto_increment=True)
            self.account = IntField('account', unique=True, null=False)
            self.password = CharField('password', null=False)
            self.name = CharField('name', null=False)
            self.class_name = CharField('class_name', null=False)
            self.profession = CharField('profession', null=False)
            self.out_date_counts = IntField('out_date_counts', default=0)

    u = UserModel('user', Connector)