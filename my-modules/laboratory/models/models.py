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
                selection=[('entrance', 'Entrance'), ('study', 'Study'),
                           ('graduate', 'Graduate'), ('cancel', 'Cancelled'), ], )
    state = fields.Selection(string='选课状态', required=True,default='unselected',
            selection=[('apply', 'Apply'), ('selected', 'Selected'),
                       ('finished', 'Finished'), ('unselected', 'Unselected'),
                       ('error', 'Error'), ])
    c_ids = fields.Many2many(
        'laboratory.courses', 'rel_students_courses',
        'student_id', 'course_id', string="已选的课程号",
        help="Analyze your self_information's correctness!", )
    # 修改学生的 选课状态。如果没有选课记录，选课状态更改为'unselected'。

    # @api.depends('c_ids')
    # def _compute_course_state(self):
    #     for record in self:
    #         # 没有任何选课信息的 记录(学生)
    #         if not record.c_ids:
    #             record.state = 'unselected'
    #         # 有选课信息，但此时的record.state='' ,因此 state需要重新赋值
    #         # elif 'apply' in record.state:
    #         #     record.state = 'apply'
    #         # elif 'error' in record.state:
    #         #     record.state = 'error'
    #         # 如果该学生已经毕业，那默认情况选课信息完成
    #         elif record.stu_status == 'graduated':
    #             record.state = 'finished'
    #         else:
    #             record.state = 'selected'

    # 修改学生的 statusBar 阶段状态_入学，攻读，毕业
    def action_stu_status_study(self):
        self.stu_status = 'study'

    def action_stu_status_entrance(self):
        self.stu_status = 'entrance'

    def action_stu_status_graduate(self):
        self.stu_status = 'graduate'

    def action_new_course(self):
        return {
            'view_mode': 'form',
            # 'view_id': self.env.ref('laboratory.courses').courseID,
            'res_model': 'laboratory.courses',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': False,
        }

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


class Courses(models.Model):
    _name = 'laboratory.courses'
    _description = 'courses'
    _rec_name = 'courseID'

    courseID = fields.Integer(required=True, string='课程号', default='1000')
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
    def action_new_stu(self):
        # if not self.website_id._get_http_domain():
        #     raise UserError(_("You haven't defined your domain"))
        return {
            'type': 'ir.actions.act_url',
            'url': 'http://localhost:8069/web#model=laboratory.students&menu_id=354',
            # 'url': 'http://www.google.com/ping?sitemap=%s/sitemap.xml' % self.website_id._get_http_domain(),
            'target': 'new',
            # 'target': 'self',
        }
        # return {
        #     # 'name': _("Robots.txt"),
        #     'view_mode': 'form',
        #     'res_model': 'laboratory.students',
        #     'type': 'ir.actions.act_window',
        #     "views": [[False, "form"]],
        #     'target': 'new',
        # }

    def action_state_apply(self):
        self.state = 'apply'

    def action_state_open(self):
        self.state = 'open'

    def action_state_done(self):
        self.state = 'done'

    def action_state_close(self):
        self.state = 'close'

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