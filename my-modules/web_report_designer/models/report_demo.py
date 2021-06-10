# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


# access_demo_label,Demo Label,model_demo_label,base.group_user,1,1,1,1


class DemoLabel(models.Model):
    _name = 'demo.label'
    _description = u'Demo 标签'

    name = fields.Char(string=u'单号', show_report=True)
    rec1 = fields.Char(string=u'记录1', show_report=True)
    msg1 = fields.Char(string=u'信息1', show_report=True)
    msg2 = fields.Char(string=u'信息2', show_report=True)
    msg3 = fields.Char(string=u'信息3', show_report=True)


class ReportDesignerDemo(models.Model):
    _inherit = 'report.designer'

    model = fields.Selection(selection_add=[('demo.label', u"领料单"), ('demo.label', u"出料单"), ], ondelete={'demo.label': 'cascade'})
