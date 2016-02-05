import os
import re
import click
import csv
import copy
import xmltodict
import json
from ..util import get_template


def prepare_sample(ctx, source):
    regex = '^sample\.' + ctx.obj['PROJECT'] + '\.[_0-9a-zA-Z\-]+\.tsv$'
    if not re.match(re.compile(regex), source):
        click.echo('Error: specified source file does not match naming convention: %s' % regex, err=True)
        ctx.abort()

    if not os.path.isfile(source):
        click.echo('Error: specified source file does not exist.', err=True)
        ctx.abort()

    # read study template xml file
    template_file = os.path.join(ctx.obj['WORKSPACE_PATH'], 'settings', 'sample.template.xml')
    sample_obj = get_template(template_file)

    del sample_obj['SAMPLE_SET']['SAMPLE'][0]
    one_sample = sample_obj['SAMPLE_SET']['SAMPLE'].pop(0)


    with open(source, 'r') as s:
        reader = csv.DictReader(s, delimiter='\t')
        for sample_info in reader:
            sample = copy.deepcopy(one_sample)

            try:
                sample['@alias'] = sample_info['icgc_sample_id']
                sample['@center_name'] = ctx.obj['SETTINGS']['centre_name']
                sample['TITLE'] = 'ICGC Sample: %s' % sample_info['icgc_sample_id']
                for sa in sample['SAMPLE_ATTRIBUTES']['SAMPLE_ATTRIBUTE']:
                    sa['VALUE'] = sample_info.get(sa['TAG']) if sample_info.get(sa['TAG']) else ''
                    if sa['TAG'] == 'phenotype' and not sa['VALUE']:
                        sa['VALUE'] = ctx.obj['SETTINGS']['projects'][ctx.obj['PROJECT']].get('phenotype')

            except KeyError, e:
                click.echo('Error: KeyError, %s' % str(e), err=True)
                ctx.abort()
            except IndexError, e:
                click.echo('Error: IndexError, %s' % str(e), err=True)
                ctx.abort()
            except Exception, e:
                click.echo('Error: %s' % str(e), err=True)
                ctx.abort()

            sample_obj['SAMPLE_SET']['SAMPLE'].append(sample)

    out_file = re.sub(r'\.tsv$', '.xml', source)
    if os.path.isfile(out_file) and not ctx.obj.get('FORCE'):
        click.echo('Error: this source file has been converted to EGA XML before, will not overwrite without "--force" option.', err=True)
        ctx.abort()

    with open(out_file, 'w') as w: w.write(xmltodict.unparse(sample_obj, pretty=True))

