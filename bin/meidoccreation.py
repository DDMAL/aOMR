from pymei.Helpers import template
from pymei.Export import meitoxml
d = template.create('mix')
meitoxml.meitoxml(d, 'yum.mei')