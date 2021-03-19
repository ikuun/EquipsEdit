from equipsedit.errors import FieldError

DEFAULT = object()

class BaseField(object):
    """
    基础字段类型

    :param _id: 字段外部ID
    :param _model: 字段所属模型
    :param _type: 字段数据库类型

    :param name: 字段名
    :param comment: 字段描述
    :param bool null: 是否为空（默认为空）
    :param default: 字段默认值
    :param bool index: 是否为索引
    :param bool primary_key: 是否为键字段
    :param bool unique: 是否为唯一约束
    :param int length: 字段长度
    :param bool is_str: 是否为文字
    :param bool auto_increment: 是否自增
    :param bool 是否为外键字段

    """
    _name = None
    _model = None
    _type = None

    name = None
    null = True
    default = None
    index = False
    primary_key = False
    unique = False
    length = 0
    is_str = False
    auto_increment = False
    is_m2o_key = False
    is_o2m_key = False
    is_m2m_key = False
    value = None

    def __init__(self, string='', **kw):
        self.comment = string

        for k, v in kw.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                raise FieldError(k)

    def _field_type_sql(self):
        '''
        生成字段类型SQL语句
        '''
        return f'{self._type}({self.length}) ' if self.length else f'{self._type} '

    def get_sql(self):
        sql = f'{self.name} '
        sql += self._field_type_sql()
        sql += 'NULL ' if self.null and not self.primary_key else 'NOT NULL '
        if self.auto_increment:
            sql += 'AUTO_INCREMENT '
        sql += f'COMMENT "{self.comment}",'

        return sql

class Char(BaseField):
    def __init__(self, *args, **kw):
        super(Char, self).__init__(*args, **kw)
        self._type = "CHAR"
        if not self.length:
            self.length = 128
        self.is_str = True

class Int(BaseField):
    def __init__(self, *args, **kw):
        super(Int, self).__init__(*args, **kw)
        self._type = "INT"

class Float(BaseField):
    """
        :param int length: 浮点型总长度
        :param int decimal: 浮点型精度（默认精度：6）
    """
    def __init__(self, *args, **kw):
        super(Float, self).__init__(*args, **kw)
        self._type = "FLOAT"
        self.length = 12 if 'length' not in kw.keys() else kw['length']
        self.decimal = 6 if 'decimal' not in kw.keys() else kw['decimal']

        if self.length < self.decimal:
            self.length = self.decimal + 1

    def _field_type_sql(self):
        return f'{self._type}({self.length},{self.decimal}) ' if self.length else f'{self._type}(,{self.decimal}) '

class Text(BaseField):
    def __init__(self, *args, **kw):
        super(Text, self).__init__(*args, **kw)
        self._type = "TEXT"

from datetime import datetime, date

class Date(BaseField):
    def __init__(self, *args, **kw):
        super(Date, self).__init__(*args, **kw)
        self._type = "DATE"
        self.is_str = True

    def today(self):
        return date.today()

class Datetime(BaseField):
    def __init__(self, *args, **kw):
        super(Datetime, self).__init__(*args, **kw)
        self._type = "DATETIME"
        self.is_str = True

    def now(self):
        return datetime.now()

class Selection(BaseField):
    """
    :param dict selects: 字段选项对应map
    """
    def __init__(self, selects, *args, **kw):
        super(Selection, self).__init__(*args, **kw)
        self.selects, self._type = self._check_input(selects)

    def _check_input(self, selects):
        if isinstance(selects, list):
            s_dict = {}
            _type = 'INT'
            for s in selects:
                if isinstance(s, tuple) and len(s) == 2:
                    s_dict[s[0]] = s[1]
                    if isinstance(s[0], str):
                        _type = 'CHAR'
                    elif isinstance(s[0], int):
                        pass
                    else:
                        raise FieldError(self.name)
                else:
                    raise FieldError(self.name)

            return s_dict, _type
        else:
            raise FieldError(self.name)

class _Foreign(BaseField):
    """
    :param comodel: 目标模型
    """

    on_delete = 'CASCADE'

    def __init__(self, *args, **kw):
        super(_Foreign, self).__init__(*args, **kw)
        self.primary_key = False
        self.unique = False
        self.index = False
        self.auto_increment = False

class Many2one(_Foreign):
    reference = None
    def __init__(self, comodel=DEFAULT, *args, **kw):
        super(Many2one, self).__init__(*args, **kw)
        if comodel != 'self':
            self.is_str = comodel.primary_key.is_str
            self.reference = comodel.primary_key
            self._type = comodel.primary_key._type

        self.comodel = comodel._get_name(comodel) if comodel != 'self' else comodel
        self.is_m2o_key = True


class One2many(_Foreign):
    def __init__(self, comodel=DEFAULT, inverse_field=DEFAULT, *args, **kw):
        super(One2many, self).__init__(*args, **kw)
        self.comodel = comodel
        self.inverse_field = inverse_field
        self.is_o2m_key = True

    def get_sql(self):
        return

class Many2many(_Foreign):
    def __init__(self, comodel=DEFAULT, rel_name=DEFAULT, column1=DEFAULT, column2=DEFAULT, *args, **kw):
        super(Many2many, self).__init__(*args, **kw)
        self.comodel = comodel
        self.rel_name = rel_name
        self.column1 = column1
        self.column2 = column2
        self.is_m2m_key = True

    def get_sql(self):
        return

    def _create_rel_table(self):
        sql = f'CREATE TABLE {self.rel_name}(' \
              f'{self.column1} INT NOT NULL, {self.column2} INT NOT NULL,' \
              f'FOREIGN KEY({self.column1}) REFERENCES %s({self._model}) ON DELETE {self.on_delete}  ON UPDATE {self.on_delete},' \
              f'FOREIGN KEY({self.column2}) REFERENCES %s({self.comodel}) ON DELETE {self.on_delete}  ON UPDATE {self.on_delete}' \
              f')ENGINE=InnoDB DEFAULT CHARSET=UTF8MB4;'

        return sql