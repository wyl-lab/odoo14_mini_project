# -*- coding: utf-8 -*-
from odoo import models, fields, api


# class laboratory(models.Model):
#     _name = 'laboratory.laboratory'
#     _description = 'laboratory.laboratory'
#
#     name = fields.Char(required=True)
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
#
#     def action_do_something(self):
#         for record in self:
#             record.name = "Something"
#         return True


class Students(models.Model):
    _name = 'laboratory.students'
    _description = 'students'
    _rec_name = 'sID'

    sID = fields.Char(required=True, string='学生号', )
    sName = fields.Char(required=True, string='学生姓名')
    sSex = fields.Selection([
        ('man', '男'), ('woman', '女'), ], string="性别", )
    sRegistDate = fields.Date(string="入学时间")
    # courseID = fields.Integer(required=True, string='課程號')
    filter_on_height = fields.Boolean(string='预估身高范围', default=False)
    height_size_min = fields.Integer(string='Size', default=130)
    height_size_max = fields.Integer(default=180)
    description = fields.Text(string='备注')
    stu_status = fields.Selection(string='所处阶段', required=True, default='entrance',
        selection=[('entrance', 'Entrance'), ('study', 'Study'), ('graduate', 'Graduate'),
        ('cancel', 'Cancelled'), ], )
    state = fields.Selection(string='选课状态', required=True, default='unselected',
        selection=[('draft', 'Draft'), ('selected', 'Selected'), ('finished', 'Finished'),
                   ('unselected', 'Unselected'), ('error', 'Error'), ])
    c_ids = fields.Many2many(
        'laboratory.courses', 'rel_students_courses',
        'student_id', 'course_id', string="所关联的课程号",
        help="Analyze your self_information's correctness!",
        # compute='_compute_course_state',
    )
    # 修改学生的 选课状态，如果选课了更改默认的state为'selected',否则依然'unselected'.

    # @api.depends('c_ids', 'state', 'sID')
    # def _compute_course_state(self):
    #     for record in self:
    #         if record.c_ids:
    #             record.state = 'unseleted'
    #         else:
    #             record.state = 'seleted'

    # 修改学生的 statusBar 阶段状态_入学，攻读，毕业
    def action_stu_status_study(self):
        self.stu_status = 'study'

    def action_stu_status_entrance(self):
        self.stu_status = 'entrance'

    def action_stu_status_graduate(self):
        self.stu_status = 'graduate'

    @api.onchange('height_size_min')
    def _onchange_height_size_min(self):
        if self.height_size_min <= 130:
            self.height_size_min = 130
        elif self.height_size_min >= self.height_size_max:
            self.height_size_min = self.height_size_max

    @api.onchange('height_size_max')
    def _onchange_height_size_max(self):
        if self.height_size_max <= self.height_size_min:
            self.height_size_max = self.height_size_min
        elif self.height_size_max >= 210:
            self.height_size_max = 210

    def move_action(self):
        self.state = 'selected'


class Courses(models.Model):
    _name = 'laboratory.courses'
    _description = 'courses'
    _rec_name = 'courseID'

    courseID = fields.Integer(required=True, string='课程号')
    courseName = fields.Char(required=True, string='课程名')
    rel_teacher = fields.Char(required=True, string='任课老师')
    description = fields.Text(string='备注')
    state = fields.Selection([
        ('apply', 'Apply'),
        ('open', 'Open'),
        ('done', 'Done'),
        ('close', 'Close'),
        ('error', 'Error'), ],
        string='状态标识',
        required=True,
        default='apply' )
    # t_ids =
    s_ids = fields.Many2many('laboratory.students', 'rel_students_courses', 'course_id', 'student_id', string="所关联的学生号", help="Analyze your course_information's correctness!")

    #: SQL constraints [(name, sql_def, message)]
    _sql_constraints = [
        ('cID_uniq', 'unique ("courseID")', "Tag courseID already exists !"),
        ('cName_uniq', 'unique ("courseName")', "Tag courseName already exists !"),
    ]

    def click_action(self):
        self.state = 'open'
# class Rel_Students_Courses(models.Model):
#     _name = 'laboratory.rel_students_courses'
#     _description = 'Rel_Students_Courses'
#
#     sID = fields.Char(required=True, string='学生号')
#     courseID = fields.Integer(required=True, string='课程号')
#     description = fields.Text(string='备注')
#     rel_sIDs = fields.Many2one('laboratory.students', 'sID', string="rel_sIDs")
#     rel_tIDs = fields.Many2one('laboratory.courses', 'tID', string="rel_tIDs")


# class Teachers(models.Model):
#     _name = 'laboratory.teachers'
#     _description = 'teachers'
#
#     tID = fields.Integer(required=True, string='課程號')
#     tName = fields.Char(required=True, string='課程名')
#     description = fields.Text(string='備注')
#     s_ids = fields.One2many('laboratory.students', 'sID', string="s_ids")


# class TestAction(models.Model):
#     _name = "test.action"
#     _description = "Test.Model"
#
#     name = fields.Char(required=True)
#
#     def action_do_something(self):
#         for record in self:
#             record.name = "Something"
#         return True