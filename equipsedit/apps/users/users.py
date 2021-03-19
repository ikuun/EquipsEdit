from equipsedit import models, fields

class UserCate(models.Model):
    _name = 'user.cate'
    _description = '用户标签'
    _init = True

    name = fields.Char(string='标签名')

class Users(models.Model):
    _name = 'users'
    _description = '用户'
    _init = True

    account = fields.Int(unique=True, null=False, string="账号")
    password = fields.Char(null=False, string="密码")
    name = fields.Char(null=False, string="用户名")
    profession = fields.Char(null=False)
    source = fields.Float('分数')
    brithday = fields.Date('生日')
    comment = fields.Text('个性签名')
    # parent_id = fields.Many2one('self', string="父母")
    cates = fields.Many2one(UserCate, string="标签")
    # cates = fields.Many2many(UserCate, 'user_cate_rel', 'user_id', 'cate_id', string="标签")

