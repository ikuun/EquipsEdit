from equipsedit import models, fields

class IrModel(models.Model):
    _name = "ir.model"
    _description = 'Model'
    _init = True

    name = fields.Char(string="模型名称")
    model = fields.Char(string="模型")
    module = fields.Char(string='模块路径')

    def create_table(self):
        super(IrModel, self).create_table()
