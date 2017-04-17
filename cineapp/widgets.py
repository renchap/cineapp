# -*- coding: utf-8 -*-

from wtforms import fields, widgets

# Define wtforms widget and field
class CKTextAreaWidget(widgets.TextArea):
    def __call__(self, field, **kwargs):
        kwargs.setdefault('class_', 'ckeditor')
        html_string = super(CKTextAreaWidget, self).__call__(field, **kwargs)
        html_string += ("""<script>
		CKEDITOR.replace( '%s', {
			enterMode: CKEDITOR.ENTER_BR
                } );	
		</script>""" % field.id)
	return widgets.HTMLString(html_string)

class CKTextAreaField(fields.TextAreaField):
	widget = CKTextAreaWidget()
