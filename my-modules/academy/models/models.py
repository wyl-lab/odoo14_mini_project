# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Teachers(models.Model):
    _name = 'academy.teachers'
    # _id = 'academy.teachers'
    # _create_uid = 'academy.teachers'
    # _description = 'academy.teachers'

    name = fields.Char()
    biography = fields.Html()
    course_ids = fields.One2many('academy.courses', 'teacher_id', string='Courses')
    # id = fields.Char()
    # create_uid = fields.Integer()
    # description = fields.Text()


class Courses(models.Model):
    _name = 'academy.courses'
    _inherit = ['mail.thread', ]
    # _inherit = 'product.template'

    name = fields.Char()
    teacher_id = fields.Many2one('academy.teachers', string="Teacher")


# class academy(models.Model):
#     _name = 'academy.academy'
#     _description = 'academy.academy'
#
#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
