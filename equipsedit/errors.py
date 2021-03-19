class FieldError(Exception):
    def __init__(self, name):
        self.name = name

    def errors(self):
        print(f'属性{self.name}不存在')