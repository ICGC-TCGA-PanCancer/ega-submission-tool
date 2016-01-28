import os
import re
import click
import yaml
import xmltodict
import json
from ..util import get_template


def prepare_study(ctx, source):
    regex = '^study\.[_0-9a-zA-Z\-]+\.yaml$'
    if not re.match(re.compile(regex), source):
        click.echo('Error: specified source file does not match naming convention: %s' % regex)
        ctx.abort()

    if not os.path.isfile(source):
        click.echo('Error: specified source file does not exist.')
        ctx.abort()

    with open(source, 'r') as s: study_info = yaml.load(s)

    # read study template xml file
    template_file = os.path.join(ctx.obj['WORKSPACE_PATH'], 'settings', 'study.template.xml')
    study_obj = get_template(template_file)

    try:
        study_obj['STUDY_SET']['STUDY']['@alias'] = study_info['study_alias']
        study_obj['STUDY_SET']['STUDY']['@center_name'] = ctx.obj['SETTINGS']['centre_name']
        study_obj['STUDY_SET']['STUDY']['DESCRIPTOR']['STUDY_TITLE'] = study_info['study_title']
        study_obj['STUDY_SET']['STUDY']['DESCRIPTOR']['STUDY_TYPE']['@existing_study_type'] = study_info['study_type']
        study_obj['STUDY_SET']['STUDY']['DESCRIPTOR']['STUDY_ABSTRACT'] = study_info['study_abstract'].rstrip()
        study_obj['STUDY_SET']['STUDY']['STUDY_ATTRIBUTES']['STUDY_ATTRIBUTE']['TAG'] = study_info['study_attr'][0]['tag']
        study_obj['STUDY_SET']['STUDY']['STUDY_ATTRIBUTES']['STUDY_ATTRIBUTE']['VALUE'] = study_info['study_attr'][0]['value']

    except KeyError, e:
        click.echo('Error: KeyError, %s' % str(e))
        ctx.abort()
    except IndexError, e:
        click.echo('Error: IndexError, %s' % str(e))
        ctx.abort()
    except Exception, e:
        click.echo('Error: %s' % str(e))
        ctx.abort()

    #click.echo(json.dumps(study_obj, indent=2))
    #click.echo(xmltodict.unparse(study_obj, pretty=True))
    out_file = re.sub(r'\.yaml$', '.xml', source)
    if os.path.isfile(out_file) and not ctx.obj.get('FORCE'):
        click.echo('Error: this study source file has been converted to study XML before, will not overwrite without "--force" option.')
        ctx.abort()

    with open(out_file, 'w') as w: w.write(xmltodict.unparse(study_obj, pretty=True))

