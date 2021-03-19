from equipsedit import sql_db
from equipsedit import fields

import inspect
import copy
import os

Connector = sql_db.Connector('127.0.0.1', 3306, 'root', 'admin', 'equipsedit')

equi_dict = {'lt': '<', 'lte': '<=', 'gt': '>', 'gte': '>=',
             'in': 'IN', 'not': '!=', 'not_null': 'NOT NULL',
             'null': 'NULL', 'like': 'LIKE'}

class MetaModel(object):

    _slots = {
        'index': [],
        'uniques': [],
        'primary_key_field': None,
        'fields': [],
        'is_m2o_key_fields': [],
        'is_o2m_key_fields': [],
        'is_m2m_key_fields': []
    }

    def __new__(cls, *args, **kwargs):
        _instrance = super().__new__(cls)
        for k in _instrance.__dir__():
            if not k.startswith('__') and isinstance(getattr(cls, k), fields.BaseField):
                _instrance.__dict__[k] = getattr(cls, k)

        return _instrance

class BaseModel(MetaModel):
    '''
    将python语句转换为sql语句，并对数据库进行增删改查操作

    :param _name: 模型名称
    :param _description: 模型描述
    :param _init: 模型是否在初始化时创建表

    :param _order: 排序字段
    :param _order_method: 排序方式
    '''
    _name = None
    _description = None
    _is_create = False
    _init = False

    _order = 'id'
    _order_method = 'ASC'

    def create_table(self):
        self.get_fields()
        self._create_table()
        self._is_create = True

    def update_table(self):
        pass

    def _get_fields(self):
        _fields = []
        for k, v in self.__dict__.items():
            if isinstance(v, fields.BaseField):
                v.name = k
                if not v.comment:
                    v.comment = k
                _fields.append(v)
                v._name = f"{self._name}.{v.name}"
                v._model = self._name

        return _fields

    def _check_primary_key_field(self, fields):
        for field in fields:
            if field.primary_key:
                return field

    def _check_unique_fields(self, fields):
        return [field for field in fields if field.unique]

    def _check_index_key(self, fields):
        return [field for field in fields if field.index]

    def _check_is_m2o_fields(self, fields):
        is_m2o_fields = []
        for field in fields:
            if field.is_m2o_key:
                is_m2o_fields.append(field)
                if field.comodel == 'self':
                    attrs = {'comodel': self._get_name(),
                             'is_str': self._slots['primary_key_field'].is_str,
                             'reference': self._slots['primary_key_field'].name,
                             '_type': self._slots['primary_key_field']._type}

                    field = getattr(self, field.name)
                    for k, v in attrs.items():
                        setattr(field, k, v)

        return is_m2o_fields

    def _check_is_o2m_fields(self, fields):
        return [field for field in fields if field.is_o2m_key]

    def _check_is_m2m_fields(self, fields):
        return [field for field in fields if field.is_m2m_key]

    def get_fields(self):
        '''
        获取所有字段信息
        :return:
        '''
        fields = self._get_fields()

        self._slots['fields'] = fields
        self._slots['primary_key'] = self._check_primary_key_field(fields)
        self._slots['uniques'] = self._check_unique_fields(fields)
        self._slots['indexs'] = self._check_index_key(fields)
        self._slots['is_m2o_key_fields'] = self._check_is_m2o_fields(fields)
        self._slots['is_o2m_key_fields'] = self._check_is_o2m_fields(fields)
        self._slots['is_m2m_key_fields'] = self._check_is_m2m_fields(fields)

    def _has_created(self):
        '''
        检测表是否被创建
        '''
        Connector.cursor.execute('SHOW TABLES;')
        ret = Connector.cursor.fetchall()
        for table in ret:
            if self._get_name() in table.values():return True

    def _create_table(self):
        '''
        创建表
        '''
        if not self._has_created():
            print(f'创建表：{self._name}...')
            sql = self._create_table_sql()
            Connector.execute(sql)
            print(f'创建表：{self._name}成功')

    def _get_name(self):
        return self._name.replace(".", "_")

    #----------------------------
    # SQL语句生成函数
    #----------------------------
    def _create_table_sql(self):
        '''
        生成创建表SQL语句
        '''
        sql = f'CREATE TABLE {self._get_name()} ('
        for v in self._slots['fields']:
            sql += v.get_sql()

        sql = f'{sql}{self._primary_key_sql()}{self._unique_sql()}' \
              f'{self._index_sql()}{self._foregin_key_sql()}'
        sql = sql[:-1] + ')ENGINE=InnoDB DEFAULT CHARSET=UTF8MB4;'
        return sql

    def _primary_key_sql(self):
        '''
        生成指定模型外键SQL语句
        '''
        return f'PRIMARY KEY({self._slots["primary_key_field"].name}),'\
            if self._slots["primary_key_field"] else ''

    def _foregin_key_sql(self):
        '''
        生成外键字段SQL语句
        '''
        sql = ''
        if self._slots["is_m2o_key_fields"]:
            for field in self._slots["is_m2o_key_fields"]:
                sql += f'FOREIGN KEY({field.name}) REFERENCES {field.comodel}({field.reference}) ON DELETE ' \
                       f'{field.on_delete}  ON UPDATE {field.on_delete},'

        return sql

    def _unique_sql(self):
        '''
        生成唯一约束SQL语句
        '''
        sql = ''
        if self._slots["uniques"]:
            sql = 'UNIQUE ('
            for field in self._slots["uniques"]:
                sql += f'{field.name},'
            sql = sql[:-1] + '),'

        return sql

    def _index_sql(self):
        '''
        生成索引SQL语句
        '''
        sql = ''
        if self._slots["indexs"]:
            sql = f'INDEX ('
            for field in self._slots["indexs"]:
                sql += f'{field.name},'
            sql = sql[:-1] + '),'

        return sql

    #TODO:完善ORM框架CUD方法
    # 2.UPDATE记录方法
    # 3.DELETE记录方法

    def create(self, vals):
        if not isinstance(vals, dict):
            raise

        cloums = ''
        values = ''

        for k, field in self.__dict__.items():
            # 跳过非字段的对象
            if not isinstance(field, fields.BaseField):
                continue

            # 获取字段默认值
            v = field.default

            # 如果默认值为函数，则执行函数
            if inspect.isfunction(v): v = v(field)
            if k in vals.keys(): v = vals[k]

            # 生成插入值语句
            if v:
                cloums += f'{k},'
                values += f'"{v}",' if getattr(self, k).is_str else f'{v},'

        sql = f'INSERT INTO {self._get_name()} ({cloums[:-1]})' \
              f' VALUES ({values[:-1]});'

        Connector.execute(sql)

    def update(self, id, vals):
        if not isinstance(vals, dict):
            raise

        if not isinstance(id, int):
            raise


    #TODO:完善ORM框架查询：
    # 1.WHERE语句输入设计、转换
    # 2.SELECT语句转换
    # 3.JOIN语句转换
    def search(self, _Q=None, **kw):
        where_sql = self._where_sql(_Q, **kw)

        sql = f'SELECT * FORM {self._get_name()} {where_sql}'

        return sql

    def _out_sql(self, _Q):
        item1, item2 = _Q.children
        sql = ''
        sql += f'({item1._out_sql(_Q)})' if isinstance(item1, Q) else _split_key_value(item1[0], item1[1], self)
        sql += f' {_Q.connector} '
        sql += f'({item2._out_sql(_Q)})' if isinstance(item2, Q) else _split_key_value(item2[0], item2[1], self)

        return sql

    def _join_sql(self):
        pass

    def _where_sql(self, Q=None, **kw):
        '''
        根据条件生成 where 语句
        :param kw:
        :return:
        '''
        sql = ''
        if Q:
            sql += f'{Q._out_sql(self)} AND '

        if kw:
            for k, v in kw.items():
                sql += f'{_split_key_value(k, v, self)} AND '

        sql = f'WHERE {sql[:-5]}'

        return sql

def _split_key_value(key, value, obj):
    if '__' in key:
        name, equi = key.split('__')
        return f'{name}{equi_dict[equi]}"{value}"' if getattr(obj, name).is_str else f'{name}{equi_dict[equi]}{value}'

    return f'{key}="{value}"' if getattr(obj, key).is_str else f'{key}={value}'

class Node():
    default = 'DEFAULT'

    def __init__(self, children=None, connector=None, negated=False):
        self.children = children[:] if children else []
        self.connector = connector or self.default
        self.negated = negated

    def __str__(self):
        template = '(NOT (%s: %s))' if self.negated else '(%s: %s)'
        return template % (self.connector, ', '.join(str(c) for c in self.children))

    def __len__(self):
        return len(self.children)

    @classmethod
    def _new_instance(cls, children=None, connector=None, negated=False):
        obj = Node(children, connector, negated)
        obj.__class__ = cls
        return obj

    def add(self, data, conn_type, squash=True):
        if data in self.children:
            return data
        if not squash:
            self.children.append(data)
            return data
        if self.connector == conn_type:
            if (isinstance(data, Node) and not data.negated and
                    (data.connector == conn_type or len(data) == 1)):
                self.children.extend(data.children)
                return self
            else:
                self.children.append(data)
                return data
        else:
            obj = self._new_instance(self.children, self.connector,
                                     self.negated)
            self.connector = conn_type
            self.children = [obj, data]
            return data

class Q(Node):
    AND = 'AND'
    OR = 'OR'
    default = AND

    def __init__(self, *args, _connector=None, _negated=False, **kwargs):
        super().__init__(children=[*args, *sorted(kwargs.items())], connector=_connector, negated=_negated)

    def _combine(self, other, conn):
        if not isinstance(other, Q):
            raise

        if not other:
            return copy.deepcopy(self)
        elif not self:
            return copy.deepcopy(other)

        obj = type(self)()
        obj.connector = conn
        obj.add(self, conn)
        obj.add(other, conn)
        return obj

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __and__(self, other):
        return self._combine(other, self.AND)


class Model(BaseModel):
    id = fields.Int(primary_key=True, auto_increment=True, index=True)
    create_time = fields.Datetime('创建时间', default=fields.Datetime.now)
    write_time = fields.Datetime('写入时间', default=fields.Datetime.now)

    def name_get(self):
        display_name = self.name if hasattr(self, 'name') else f'{self._name} {self.id}'
        self.display_name = display_name

        return (display_name, self.id)