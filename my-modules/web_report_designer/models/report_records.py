# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


# access_demo_label,Demo Label,model_demo_label,base.group_user,1,1,1,1


class DemoRecords(models.Model):
    _name = 'demo.records'
    _description = u'Demo 记录'

    name = fields.Char(string=u'records', show_report=True)
    rec1 = fields.Char(string=u'记录1', show_report=True)
    rec2 = fields.Char(string=u'记录2', show_report=True)
    rec3 = fields.Char(string=u'记录3', show_report=True)
    rec4 = fields.Char(string=u'记录4', show_report=True)


class ReportDesignerDemo(models.Model):
    _inherit = 'report.designer'

    model = fields.Selection(selection_add=[('demo.records', u"物料单")], ondelete={'demo.records': 'cascade'})
