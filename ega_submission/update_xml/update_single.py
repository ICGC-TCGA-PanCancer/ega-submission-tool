import os
import re
import click
import calendar
import time
import uuid
import xmltodict
import fnmatch
from ..util import get_template, file_pattern_exist, submit, prepare_submission, get_submitted_items_from_receipt, update_original_xml_with_ega_accession


def update_single(ctx, ega_type, source):
    if not (os.path.isfile(source) and source.endswith('.xml')):
        click.echo('Error: specified file does not exist or does not have .xml extension - %s' % source, err=True)
        ctx.abort()

    # parse all relavent submission receipts to identify items have been submitted before
    submitted_items = {}
    receipt_file_pattern = '%s.*.receipt-test_*.xml' % ega_type if ctx.obj['IS_TEST'] else '%s.*.receipt-*.xml' % ega_type
    for filename in [f for f in os.listdir('.') if os.path.isfile(f)]:
        if not ctx.obj['IS_TEST'] and 'receipt-test_' in filename: continue

        if fnmatch.fnmatch(filename, receipt_file_pattern):
            submitted_items.update(get_submitted_items_from_receipt(os.path.join(os.getcwd(), filename), ega_type, ''))
                
    update_original_xml_with_ega_accession(ega_type, os.path.join(os.getcwd(), source), submitted_items)

    submission_obj = prepare_submission(ctx, ega_type, [source], 'MODIFY')
    submission_alias = submission_obj['SUBMISSION_SET']['SUBMISSION']['@alias']

    submission_file = re.sub(r'\.xml$', '.submission-' + submission_alias + '.xml', source)

    if not ctx.obj['IS_TEST'] and not ctx.obj.get('FORCE') \
        and file_pattern_exist(ctx.obj['CURRENT_DIR'], source.rstrip('xml')+'submission-[0-9]+_.+'):
        click.echo('Error: this %s xml may have been submitted before, will not submit without "--force" option.' % ega_type, err=True)
        ctx.abort()

    with open(submission_file, 'w') as w: w.write(xmltodict.unparse(submission_obj, pretty=True))

    submission_file = os.path.join(os.getcwd(), submission_file)
    metadata_xmls = [os.path.join(os.getcwd(), source)]

    if not submit(ctx, ega_type, submission_file, metadata_xmls, 'MODIFY'):
        click.echo('Submission failed, see above for more details.\n\n', err=True)
        ctx.abort()
