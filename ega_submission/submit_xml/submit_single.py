import os
import re
import click
import calendar
import time
import uuid
import xmltodict
from ..util import get_template, file_pattern_exist, submit, prepare_submission


def submit_single(ctx, ega_type, source):
    if not (os.path.isfile(source) and source.endswith('.xml')):
        click.echo('Error: specified file does not exist or does not have .xml extension - %s' % source, err=True)
        ctx.abort()

    submission_obj = prepare_submission(ctx, ega_type, [source])
    submission_alias = submission_obj['SUBMISSION_SET']['SUBMISSION']['@alias']

    submission_file = re.sub(r'\.xml$', '.submission-' + submission_alias + '.xml', source)

    if not ctx.obj['IS_TEST'] and not ctx.obj.get('FORCE') \
        and file_pattern_exist(ctx.obj['CURRENT_DIR'], source.rstrip('xml')+'submission-[0-9]+_.+'):
        click.echo('Error: this %s xml may have been submitted before, will not submit without "--force" option.' % ega_type, err=True)
        ctx.abort()

    with open(submission_file, 'w') as w: w.write(xmltodict.unparse(submission_obj, pretty=True))

    submission_file = os.path.join(os.getcwd(), submission_file)
    metadata_xmls = [os.path.join(os.getcwd(), source)]

    if not submit(ctx, ega_type, submission_file, metadata_xmls):
        click.echo('Submission failed, see above for more details.\n\n', err=True)
        ctx.abort()
