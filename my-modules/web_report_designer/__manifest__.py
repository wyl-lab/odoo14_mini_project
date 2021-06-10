# -*- coding: utf-8 -*-

{
    'name': '报表设计器',
    'version': '1.0',
    "author": "ERP Team",
    "website": "http://yt.hstech-china.com",
    'category': 'web',
    'depends': ['web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/sheet_rpc.xml',
        'views/report_designer_view.xml',
        'views/data.xml',
    ],
    'description': '''
		安装模块reportbro-lib==1.3.4;
		doc reportbro-lib-master reportbro替换Lib site-packages reportbro;
		web_report_designer/controllers/fonts/yahei.pkl 中 yahei.ttf路径修改成正确的
		字段上加show_report=True;排序方法继承;
		data.js加入数据;
		单独JS写入清除-非必须;
		参数名称不能有空格''',
    'qweb': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
