import os
import re
import json
import click
import calendar
import time
import uuid
import xmltodict
from ..util import get_template, file_pattern_exist, submit


def submit_study(ctx, source):
    if not (os.path.isfile(source) and source.endswith('.xml')):
        click.echo('Error: specified file does not exist or does not have .xml extension - %s' % source)
        ctx.abort()

    # read submission template xml file
    template_file = os.path.join(ctx.obj['WORKSPACE_PATH'], 'settings', 'submission.template.xml')
    submission_obj = get_template(template_file)

    epoch_time = str(int(calendar.timegm(time.gmtime())))
    uuid_str = str(uuid.uuid4())
    alias_parts = [epoch_time, uuid_str]
    if ctx.obj['IS_TEST']: alias_parts.insert(0, 'test')
    submission_alias = '_'.join(alias_parts)

    try:
        submission_obj['SUBMISSION_SET']['SUBMISSION']['@alias'] = submission_alias
        actions = submission_obj['SUBMISSION_SET']['SUBMISSION']['ACTIONS']['ACTION']
        action = actions.pop(0)  # remove the first placeholder action
        action['ADD']['@source'] = source
        action['ADD']['@schema'] = 'study'

        actions.insert(0, action)  # add action back in the first place
    except Exception, e:
        click.echo('Error: %s' % str(e))
        ctx.abort()

    #click.echo(json.dumps(submission_obj, indent=2))
    #click.echo(xmltodict.unparse(submission_obj, pretty=True))
    submission_file = re.sub(r'\.xml$', '.submission-' + submission_alias + '.xml', source)

    if not ctx.obj['IS_TEST']:
        if not ctx.obj.get('FORCE') \
            and file_pattern_exist(ctx.obj['CURRENT_DIR'], r'.+\.submission-[0-9]+_.+'):
            click.echo('Error: this study xml may have been submitted before, will not submit without "--force" option.')
            ctx.abort()

    with open(submission_file, 'w') as w: w.write(xmltodict.unparse(submission_obj, pretty=True))

    submission_file = os.path.join(os.getcwd(), submission_file)
    metadata_xmls = [os.path.join(os.getcwd(), source)]

    submit(ctx, submission_file, metadata_xmls)
